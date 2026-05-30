"""Flask server — HTTP routes and application entry point.

Routes:
  POST /v1/responses          — Responses API SSE streaming (HTTP fallback)
  WS   /v1/responses          — Responses API WebSocket (primary)
  POST /v1/chat/completions   — Chat Completions passthrough (SSE streaming)
  GET  /v1/models             — LiteLLM model list passthrough
  GET  /health                — Health check

The server is a thin layer that delegates protocol conversion to
converter.py and SSE event construction to sse_builder.py.
"""

import json
import logging
import os
import sys
import time

import requests
from flask import Flask, Response, request
from flask_sock import Sock
from waitress import serve

# File logger for debugging
_ts = time.strftime("%Y%m%d-%H%M%S")
logging.basicConfig(
    filename=f"D:/maozhua/Codex/proxy_{_ts}.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
_log = logging.getLogger("proxy")

from src.config import (
    LITELLM_URL,
    PROXY_HOST,
    PROXY_PORT,
    UPSTREAM_TIMEOUT_CONNECT,
    UPSTREAM_TIMEOUT_READ,
    MAX_RETRIES,
    KNOWN_MODELS,
    DEFAULT_MODEL,
    get_litellm_headers,
    get_system_prompt,
)
from src.converter import responses_to_chat
from src.sse_builder import (
    RetryableStreamError,
    format_sse,
    build_sse_events,
    stream_sse_events,
)

app = Flask(__name__)
sock = Sock(app)


def _message_has_images(messages: list) -> bool:
    """Check if any message contains image_url content blocks."""
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    return True
    return False


# ──────────────────────────────────────────────
#  Routes
# ──────────────────────────────────────────────


@app.route("/v1/responses", methods=["POST"])
def handle_responses():
    """HTTP fallback: convert Responses API request → LiteLLM → SSE stream."""
    body = request.get_json(force=True)
    chat_body = responses_to_chat(body)
    # Use model from converter (which auto-switches to qwen-vl-plus for images)
    model = chat_body.get("model", "deepseek-v4")
    resp_id = body.get("response_id", f"resp_{int(time.time() * 1000)}")

    tools = len(chat_body.get("tools", []))
    input_len = len(body.get("input", []))
    instructions = body.get("instructions", "")[:200]

    # Dump last 5 messages for debugging
    msgs = chat_body.get("messages", [])
    _log.info("[REQ] model=%s total_msgs=%d tools=%d", model, len(msgs), tools)
    print(f"[REQ] total_msgs={len(msgs)}  --- last 8 msgs ---")
    for m in msgs[-8:]:
        role = m.get("role", "?")
        content = str(m.get("content", ""))[:120]
        tc = len(m.get("tool_calls", []))
        tc_ids = [t.get("id","")[:8] for t in m.get("tool_calls", [])]
        tool_id = m.get("tool_call_id", "")[:8]
        extra = f"tool_calls={tc_ids}" if tc else (f"tool_id={tool_id}" if tool_id else "")
        print(f"[REQ]   {role:12s} | {content[:80]:80s} | {extra}")
    print(f"[REQ] ---")

    try:
        resp = requests.post(
            f"{LITELLM_URL}/v1/chat/completions",
            json=chat_body,
            stream=True,
            timeout=(UPSTREAM_TIMEOUT_CONNECT, UPSTREAM_TIMEOUT_READ),
            headers=get_litellm_headers(),
        )
        if resp.status_code != 200:
            err = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
            status = resp.status_code if 400 <= resp.status_code < 500 else 502
            _log.error("[ERR] upstream status=%d body=%s", resp.status_code, err[:200])
            print(f"[ERR] upstream status={resp.status_code} body={err[:150]}")
            return {"error": {"message": err, "type": "upstream_error"}}, status

        _log.info("[OK] streaming started for model=%s", model)
        print("[OK] streaming started")
        return Response(
            stream_sse_events(chat_body, model, resp_id, resp),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except requests.exceptions.RequestException as e:
        print(f"[ERR] {e}")
        return {"error": {"message": str(e), "type": "proxy_error"}}, 502


@app.route("/v1/chat/completions", methods=["POST"])
def handle_chat_completions():
    """Chat Completions passthrough: inject system prompt, alias model, forward to LiteLLM."""
    body = request.get_json(force=True)

    # Model aliasing
    model = body.get("model", DEFAULT_MODEL)
    if model in KNOWN_MODELS:
        model = DEFAULT_MODEL

    # Auto-detect images → route to vision model
    if _message_has_images(body.get("messages", [])):
        model = "qwen-vl-plus"
        print(f"[AUTO-ROUTE] image detected → qwen-vl-plus")

    body["model"] = model

    # Inject agent system prompt
    agent_prompt = get_system_prompt()
    if agent_prompt:
        messages = body.get("messages", [])
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = agent_prompt + "\n" + messages[0]["content"]
        else:
            messages.insert(0, {"role": "system", "content": agent_prompt})
        body["messages"] = messages

    msgs = body.get("messages", [])
    tools = len(body.get("tools", []))
    _log.info("[CHAT] model=%s total_msgs=%d tools=%d", model, len(msgs), tools)
    print(f"[CHAT] model={model} msgs={len(msgs)} tools={tools}")

    try:
        resp = requests.post(
            f"{LITELLM_URL}/v1/chat/completions",
            json=body,
            stream=True,
            timeout=(UPSTREAM_TIMEOUT_CONNECT, UPSTREAM_TIMEOUT_READ),
            headers=get_litellm_headers(),
        )
        if resp.status_code != 200:
            err = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
            status = resp.status_code if 400 <= resp.status_code < 500 else 502
            _log.error("[ERR] upstream status=%d body=%s", resp.status_code, err[:200])
            print(f"[ERR] upstream status={resp.status_code} body={err[:150]}")
            return {"error": {"message": err, "type": "upstream_error"}}, status

        _log.info("[OK] chat streaming started for model=%s", model)
        print("[OK] chat streaming started")
        return Response(
            resp.iter_content(chunk_size=None),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except requests.exceptions.RequestException as e:
        print(f"[ERR] {e}")
        return {"error": {"message": str(e), "type": "proxy_error"}}, 502


def _generate_with_retry(chat_body: dict, model: str, resp_id: str):
    """Generator wrapper with retry logic around stream_sse_events.

    Retries transient (5xx / network) errors up to MAX_RETRIES times
    with exponential backoff. 4xx errors are fatal.
    """
    msgs = len(chat_body.get("messages", []))
    tools = len(chat_body.get("tools", []))

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"[REQ] model={model} msgs={msgs} tools={tools} stream=True attempt={attempt}")

        try:
            resp = requests.post(
                f"{LITELLM_URL}/v1/chat/completions",
                json=chat_body,
                stream=True,
                timeout=(UPSTREAM_TIMEOUT_CONNECT, UPSTREAM_TIMEOUT_READ),
                headers=get_litellm_headers(),
            )
        except requests.exceptions.RequestException as e:
            print(f"[ERR] {e}")
            if attempt < MAX_RETRIES:
                delay = 2 ** (attempt - 1)
                print(f"[RETRY] attempt={attempt + 1} delay={delay}s")
                time.sleep(delay)
                continue
            yield format_sse("error", {
                "type": "error",
                "error": {"message": str(e), "type": "proxy_error"},
            })
            yield "data: [DONE]\n\n"
            return

        if resp.status_code != 200:
            err = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
            print(f"[ERR] upstream status={resp.status_code} body={err[:150]}")

            if 400 <= resp.status_code < 500:
                yield format_sse("error", {
                    "type": "error",
                    "error": {"message": err, "type": "upstream_error"},
                })
                yield "data: [DONE]\n\n"
                return

            if attempt < MAX_RETRIES:
                delay = 2 ** (attempt - 1)
                print(f"[RETRY] attempt={attempt + 1} delay={delay}s")
                time.sleep(delay)
                continue

            yield format_sse("error", {
                "type": "error",
                "error": {"message": err, "type": "upstream_error"},
            })
            yield "data: [DONE]\n\n"
            return

        print("[OK] streaming started")
        try:
            yield from stream_sse_events(chat_body, model, resp_id, resp)
            return
        except RetryableStreamError as e:
            if attempt < MAX_RETRIES:
                delay = 2 ** (attempt - 1)
                print(f"[RETRY] attempt={attempt + 1} delay={delay}s")
                time.sleep(delay)
                continue
            yield format_sse("error", {
                "type": "error",
                "error": {"message": str(e), "type": "stream_error"},
            })
            yield "data: [DONE]\n\n"
            return


@app.route("/v1/models", methods=["GET"])
def handle_models():
    """Return the model list from LiteLLM."""
    try:
        resp = requests.get(f"{LITELLM_URL}/v1/models", timeout=10, headers=get_litellm_headers())
        return resp.json(), resp.status_code
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}, 502


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return {"status": "ok", "target": LITELLM_URL}


# ──────────────────────────────────────────────
#  WebSocket route: /v1/responses
# ──────────────────────────────────────────────


def _sse_to_json(sse_str: str) -> str | None:
    """Convert an SSE formatted event to a JSON string for WebSocket transport.

    SSE:  event: response.created\\ndata: {"type":...}\\n\\n
    JSON: {"type": "response.created", ...}

    Returns None for [DONE] markers and empty data.
    """
    if not sse_str or sse_str.startswith(":"):
        return None
    # Extract the "data:" field
    for line in sse_str.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload == "[DONE]":
                return None
            return payload
    return None


@sock.route("/v1/responses")
def ws_responses(ws):
    """WebSocket Responses API handler.

    Receives Responses API request as JSON over WebSocket,
    converts to Chat Completions, sends back JSON events
    (NOT raw SSE — OpenAI WS protocol uses pure JSON).
    """
    t0 = time.time()
    _log.info("[WS] connected")
    print("[WS] connected")

    try:
        raw = ws.receive(timeout=30)
        if raw is None:
            _log.warning("[WS] no data received within timeout")
            print("[WS] no data received within timeout")
            return
    except Exception as e:
        _log.error("[WS] receive error: %s", e)
        print(f"[WS] receive error: {e}")
        return

    _log.info("[WS] rcvd %d bytes", len(raw))
    print(f"[WS] rcvd {len(raw)} bytes in {time.time() - t0:.1f}s")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        _log.error("[WS] invalid JSON")
        ws.send(json.dumps({"type": "error", "error": {"message": "invalid JSON"}}))
        return

    if isinstance(data, dict) and data.get("type") == "response.create":
        body = data.get("response", {})
    else:
        body = data

    chat_body = responses_to_chat(body)
    model = chat_body.get("model", DEFAULT_MODEL)
    resp_id = body.get("response_id", f"resp_{int(time.time() * 1000)}")

    tools = len(chat_body.get("tools", []))
    msgs = len(chat_body.get("messages", []))
    _log.info("[WS] model=%s msgs=%d tools=%d", model, msgs, tools)
    print(f"[WS] model={model} msgs={msgs} tools={tools}")

    try:
        resp = requests.post(
            f"{LITELLM_URL}/v1/chat/completions",
            json=chat_body,
            stream=True,
            timeout=(UPSTREAM_TIMEOUT_CONNECT, UPSTREAM_TIMEOUT_READ),
            headers=get_litellm_headers(),
        )
        if resp.status_code != 200:
            err = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
            _log.error("[WS] upstream status=%d", resp.status_code)
            ws.send(json.dumps({"type": "error", "error": {"message": err, "type": "upstream_error"}}))
            return

        _log.info("[WS] streaming")
        print("[WS] streaming")
        for sse_str in stream_sse_events(chat_body, model, resp_id, resp):
            json_event = _sse_to_json(sse_str)
            if json_event is not None:
                ws.send(json_event)
        elapsed = time.time() - t0
        _log.info("[WS] done in %.1fs", elapsed)
        print(f"[WS] done in {elapsed:.1f}s")
    except requests.exceptions.RequestException as e:
        _log.error("[WS] request error: %s", e)
        ws.send(json.dumps({"type": "error", "error": {"message": str(e), "type": "proxy_error"}}))


# ──────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────


def main():
    """Start the proxy with Waitress WSGI server (multi-threaded, production-grade)."""
    print(f"Codex SSE Proxy: http://{PROXY_HOST}:{PROXY_PORT} -> {LITELLM_URL}")
    print(f"Waitress WSGI server (4 threads) — each thread isolated from crashes")
    serve(app, host=PROXY_HOST, port=PROXY_PORT, threads=4)


if __name__ == "__main__":
    main()
