"""SSE event builder — constructs and formats Server-Sent Events.

Handles both non-streaming (build_sse_events) and streaming
(stream_sse_events) response patterns for the Anthropic Responses API.
"""

import json
import logging
import time
from collections import OrderedDict

import requests

from src.config import LITELLM_URL, UPSTREAM_TIMEOUT_CONNECT, UPSTREAM_TIMEOUT_READ, UPSTREAM_TIMEOUT_TOTAL, MAX_RETRIES

_log = logging.getLogger("proxy")


class RetryableStreamError(Exception):
    """Stream error that can be retried (network disconnect, timeout)."""


# Reasoning content cache — DeepSeek thinking mode requires reasoning_content
# to be round-tripped in multi-turn tool-call conversations.
# Keyed by tool call ID so the same function_call can be looked up across multiple
# requests (Codex replays full conversation history each turn).
# LRU-eviction: max 500 entries to prevent unbounded memory growth in long sessions.
_reasoning_map: OrderedDict[str, str] = OrderedDict()
_MAX_REASONING_ENTRIES = 500


def _lru_set(key: str, value: str):
    """Set a key with LRU eviction if at capacity."""
    if key in _reasoning_map:
        del _reasoning_map[key]
    elif len(_reasoning_map) >= _MAX_REASONING_ENTRIES:
        _reasoning_map.popitem(last=False)  # evict oldest
    _reasoning_map[key] = value


def cache_reasoning_for_calls(reasoning: str, call_ids: list[str]):
    """Store reasoning content keyed by tool call IDs."""
    for cid in call_ids:
        if cid:
            _lru_set(cid, reasoning)


def get_reasoning_for_call(call_id: str) -> str | None:
    """Look up cached reasoning by call ID. Returns None if not found."""
    return _reasoning_map.get(call_id)


def format_sse(event_type: str, data: dict) -> str:
    """Format a dict as a Server-Sent Event string."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def build_sse_events(chat_resp: dict, model: str, resp_id: str):
    """Construct non-streaming SSE events from a complete Chat Completions response.

    Used as fallback when the upstream does not support streaming.
    """
    choice = chat_resp.get("choices", [{}])[0]
    msg = choice.get("message", {})
    usage = chat_resp.get("usage", {})
    created = chat_resp.get("created", int(time.time()))

    events: list[tuple[str, dict]] = []

    base_response = {
        "id": resp_id, "object": "response",
        "created_at": created, "model": model,
    }

    events.append(("response.created", {
        "type": "response.created",
        "response": {**base_response, "status": "in_progress", "output": []}
    }))
    events.append(("response.in_progress", {
        "type": "response.in_progress",
        "response": {**base_response, "status": "in_progress", "output": []}
    }))

    # Reasoning content
    raw_reasoning_content = msg.get("reasoning_content") or msg.get("reasoning")
    reasoning_content = raw_reasoning_content if raw_reasoning_content else ""
    if raw_reasoning_content and len(str(raw_reasoning_content).strip()) > 0:
        events.append(("response.reasoning.added", {
            "type": "response.reasoning.added",
            "response_id": resp_id,
            "summary": [],
        }))
        events.append(("response.reasoning.delta", {
            "type": "response.reasoning.delta",
            "response_id": resp_id,
            "delta": reasoning_content,
        }))
        events.append(("response.reasoning.done", {
            "type": "response.reasoning.done",
            "response_id": resp_id,
            "summary": [{"type": "reasoning_text", "text": reasoning_content}],
            "status": "completed",
        }))
        print(f"[REASONING] detected (1 chunks, {len(reasoning_content)} chars)")

    output_items = []
    content_text = msg.get("content")
    tool_calls = msg.get("tool_calls", [])
    output_index = 0

    if content_text:
        item = {
            "id": f"{resp_id}:output:{output_index}",
            "type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": content_text}],
        }
        output_items.append(item)
        events.append(("response.output_item.added", {
            "type": "response.output_item.added", "output_index": output_index, "item": item,
        }))
        events.append(("response.output_item.done", {
            "type": "response.output_item.done", "output_index": output_index, "item": item,
        }))
        output_index += 1

    for tc in tool_calls:
        fn = tc.get("function", {})
        item = {
            "id": tc.get("id", f"{resp_id}:call_{output_index}"),
            "type": "function_call", "call_id": tc.get("id", ""),
            "name": fn.get("name", ""), "arguments": fn.get("arguments", "{}"),
            "status": "completed",
        }
        output_items.append(item)
        events.append(("response.output_item.added", {
            "type": "response.output_item.added", "output_index": output_index, "item": item,
        }))
        events.append(("response.output_item.done", {
            "type": "response.output_item.done", "output_index": output_index, "item": item,
        }))
        output_index += 1

    events.append(("response.completed", {
        "type": "response.completed",
        "response": {
            **base_response, "status": "completed", "output": output_items,
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        },
    }))

    # Cache reasoning for next request (DeepSeek thinking mode round-trip)
    raw_rc = msg.get("reasoning_content") or msg.get("reasoning")
    if raw_rc is not None and tool_calls:
        call_ids = [tc.get("id", "") for tc in tool_calls]
        cache_reasoning_for_calls(str(raw_rc), call_ids)

    return events


def stream_sse_events(chat_body: dict, model: str, resp_id: str, resp):
    """Generator: stream SSE events from a streaming LiteLLM response.

    Yields formatted SSE strings for real-time delivery.
    """
    created = int(time.time())
    base_response = {
        "id": resp_id, "object": "response",
        "created_at": created, "model": model,
    }

    # Initial events
    yield format_sse("response.created", {
        "type": "response.created",
        "response": {**base_response, "status": "in_progress", "output": []}
    })
    yield format_sse("response.in_progress", {
        "type": "response.in_progress",
        "response": {**base_response, "status": "in_progress", "output": []}
    })

    output_index = 0
    output_items = []
    content_chunks: list[str] = []
    reasoning_chunks: list[str] = []
    reasoning_started = False
    reasoning_ended = False
    tool_calls: list[dict] = []
    item_id = f"{resp_id}:output:{output_index}"
    msg_item_started = False
    usage: dict = {}
    first_chunk = True
    chunk_count = 0
    t0 = time.time()

    try:
        for line in resp.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8")
            if not line_str.startswith("data: "):
                continue
            data_str = line_str[6:]
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            chunk_count += 1
            if first_chunk:
                first_chunk = False
                _log.info("[STREAM] first chunk after %.1fs", time.time() - t0)

            # Total timeout check — abort if cumulative time exceeded
            elapsed_total = time.time() - t0
            if elapsed_total > UPSTREAM_TIMEOUT_TOTAL:
                _log.error("[STREAM] total timeout %.1fs > %ds, aborting",
                          elapsed_total, UPSTREAM_TIMEOUT_TOTAL)
                raise RetryableStreamError(
                    f"total timeout {elapsed_total:.0f}s > {UPSTREAM_TIMEOUT_TOTAL}s"
                )

            choice = chunk.get("choices", [{}])[0]
            delta = choice.get("delta", {})

            # Reasoning content (DeepSeek R1 / V4 Pro)
            raw_reasoning = delta.get("reasoning_content") or delta.get("reasoning")
            if raw_reasoning:
                reasoning_text = str(raw_reasoning)
                reasoning_chunks.append(reasoning_text)
                if not reasoning_started:
                    reasoning_started = True
                    yield format_sse("response.reasoning.added", {
                        "type": "response.reasoning.added",
                        "response_id": resp_id,
                        "summary": [],
                    })
                yield format_sse("response.reasoning.delta", {
                    "type": "response.reasoning.delta",
                    "response_id": resp_id,
                    "delta": reasoning_text,
                })

            # Reasoning → content transition + text deltas
            if "content" in delta:
                if reasoning_started and not reasoning_ended:
                    reasoning_ended = True
                    full_reasoning = "".join(reasoning_chunks)
                    yield format_sse("response.reasoning.done", {
                        "type": "response.reasoning.done",
                        "response_id": resp_id,
                        "summary": [{"type": "reasoning_text", "text": full_reasoning}],
                        "status": "completed",
                    })
                    print(f"[REASONING] detected ({len(reasoning_chunks)} chunks, {len(full_reasoning)} chars)")

                text = delta["content"]
                if text:
                    content_chunks.append(text)
                    if not msg_item_started:
                        msg_item_started = True
                        item = {
                            "id": item_id, "type": "message", "role": "assistant",
                            "status": "in_progress",
                            "content": [{"type": "output_text", "text": ""}],
                        }
                        yield format_sse("response.output_item.added", {
                            "type": "response.output_item.added",
                            "output_index": output_index, "item": item,
                        })
                    yield format_sse("response.content_part.delta", {
                        "type": "response.content_part.delta",
                        "output_index": output_index, "content_index": 0,
                        "delta": text,
                    })

            # Tool calls (accumulate by index across chunks)
            if "tool_calls" in delta:
                for tc in delta["tool_calls"]:
                    idx = tc.get("index", len(tool_calls))
                    while len(tool_calls) <= idx:
                        tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                    if "id" in tc:
                        tool_calls[idx]["id"] = tc["id"]
                    if "function" in tc:
                        if "name" in tc["function"]:
                            tool_calls[idx]["function"]["name"] = tc["function"]["name"]
                        if "arguments" in tc["function"]:
                            tool_calls[idx]["function"]["arguments"] += tc["function"]["arguments"]

            # Track usage from final chunk
            if "usage" in chunk:
                usage = chunk["usage"]

        # ── Stream finished: emit completion events ──

        # Finalize reasoning if still in progress (reasoning-only response)
        if reasoning_started and not reasoning_ended:
            reasoning_ended = True
            full_reasoning = "".join(reasoning_chunks)
            yield format_sse("response.reasoning.done", {
                "type": "response.reasoning.done",
                "response_id": resp_id,
                "summary": [{"type": "reasoning_text", "text": full_reasoning}],
                "status": "completed",
            })
            print(f"[REASONING] detected ({len(reasoning_chunks)} chunks, {len(full_reasoning)} chars)")

        # Finalize message item if we had text content
        if msg_item_started and content_chunks:
            full_text = "".join(content_chunks)
            item = {
                "id": item_id, "type": "message", "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": full_text}],
            }
            output_items.append(item)
            yield format_sse("response.output_item.done", {
                "type": "response.output_item.done",
                "output_index": output_index, "item": item,
            })
            output_index += 1

        # Emit tool call items (non-streaming for tools)
        for tc in tool_calls:
            if not tc["id"]:
                continue
            fn = tc.get("function", {})
            item = {
                "id": tc["id"], "type": "function_call",
                "call_id": tc["id"],
                "name": fn.get("name", ""),
                "arguments": fn.get("arguments", "{}"),
                "status": "completed",
            }
            output_items.append(item)
            yield format_sse("response.output_item.added", {
                "type": "response.output_item.added",
                "output_index": output_index, "item": item,
            })
            yield format_sse("response.output_item.done", {
                "type": "response.output_item.done",
                "output_index": output_index, "item": item,
            })
            output_index += 1

        # Cache reasoning for next request (DeepSeek thinking mode round-trip)
        if reasoning_started and tool_calls:
            full_reasoning = "".join(reasoning_chunks)
            call_ids = [tc["id"] for tc in tool_calls if tc["id"]]
            cache_reasoning_for_calls(full_reasoning, call_ids)
            _log.info("[REASONING] cached %d chars for %d call_ids", len(full_reasoning), len(call_ids))

        # Final completed event
        elapsed = time.time() - t0
        _log.info("[STREAM] done chunks=%d content=%d chars tools=%d tok_in=%d tok_out=%d time=%.1fs",
                  chunk_count, len("".join(content_chunks)), len(tool_calls),
                  usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), elapsed)
        yield format_sse("response.completed", {
            "type": "response.completed",
            "response": {
                **base_response, "status": "completed", "output": output_items,
                "usage": {
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            },
        })
        yield "data: [DONE]\n\n"

    except requests.exceptions.RequestException as e:
        _log.exception("[STREAM] upstream error: %s", e)
        raise RetryableStreamError(str(e))
    except GeneratorExit:
        # Client disconnected — clean exit, don't treat as error
        _log.info("[STREAM] client disconnected, cleaning up")
        raise
    except Exception as e:
        _log.exception("[STREAM] unhandled error: %s", e)
        yield format_sse("error", {
            "type": "error",
            "error": {"message": str(e), "type": "stream_error"},
        })
        yield "data: [DONE]\n\n"
    finally:
        # Always close the upstream response to prevent connection leaks
        try:
            resp.close()
        except Exception:
            pass
