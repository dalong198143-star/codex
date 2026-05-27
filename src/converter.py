"""Protocol converter — Responses API → Chat Completions API.

Handles the core conversion logic: input parsing, tool filtering,
model aliasing, and system prompt injection.
"""

import json

from src.config import get_system_prompt, is_model_aliased, DEFAULT_MODEL
from src.sse_builder import get_reasoning_for_call


def filter_tools(tools):
    """Convert Responses API tools list to Chat Completions format."""
    if not tools:
        return None
    result = []
    for t in tools:
        if t.get("type") != "function":
            continue
        result.append({
            "type": "function",
            "function": {
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "parameters": t.get("parameters", {}),
            }
        })
    return result if result else None


def responses_to_chat(body: dict) -> dict:
    """Convert a Responses API request body to a Chat Completions body."""
    model = body.get("model", DEFAULT_MODEL)
    if is_model_aliased(model):
        model = DEFAULT_MODEL
    chat: dict = {"model": model}

    inp = body.get("input", [])
    messages = []

    # Inject agent system prompt
    agent_prompt = get_system_prompt()
    instructions = body.get("instructions", "")
    if agent_prompt:
        if instructions:
            instructions = agent_prompt + "\n" + instructions
        else:
            instructions = agent_prompt
    if instructions:
        messages.append({"role": "system", "content": instructions})

    if isinstance(inp, str):
        messages.append({"role": "user", "content": inp})
    elif isinstance(inp, list):
        # Pre-scan: collect call_ids that have matching function_call_output items.
        # Only convert function_calls whose outputs exist — pending tool calls from
        # the latest response (no outputs yet) must be skipped, otherwise DeepSeek
        # rejects the request with "insufficient tool messages following tool_calls".
        completed_call_ids = set()
        for item in inp:
            if isinstance(item, dict) and item.get("type") == "function_call_output":
                cid = item.get("call_id", "")
                if cid:
                    completed_call_ids.add(cid)

        i = 0
        while i < len(inp):
            item = inp[i]
            if not isinstance(item, dict):
                messages.append({"role": "user", "content": str(item)})
                i += 1
                continue

            item_type = item.get("type", "")

            if item_type == "message":
                role = item.get("role", "user")
                content_list = item.get("content", [])
                if isinstance(content_list, list):
                    texts = []
                    for c in content_list:
                        if isinstance(c, dict):
                            ct = c.get("type", "")
                            if ct in ("output_text", "input_text"):
                                texts.append(c.get("text", ""))
                            elif "text" in c:
                                texts.append(c["text"])
                        elif isinstance(c, str):
                            texts.append(c)
                    content = "\n".join(texts)
                else:
                    content = str(content_list)
                messages.append({"role": role, "content": content})
                i += 1

            elif item_type == "function_call":
                tcs = []
                skipped = 0
                while i < len(inp) and isinstance(inp[i], dict) and inp[i].get("type") == "function_call":
                    fc = inp[i]
                    fc_id = fc.get("call_id", fc.get("id", ""))
                    if fc_id in completed_call_ids:
                        tcs.append({
                            "id": fc_id,
                            "type": "function",
                            "function": {
                                "name": fc.get("name", ""),
                                "arguments": fc.get("arguments", "{}"),
                            },
                        })
                    else:
                        skipped += 1
                    i += 1
                if skipped:
                    print(f"[CONVERTER] skip {skipped} pending function_calls (no matching output)")
                if tcs:
                    msg = {"role": "assistant", "content": None, "tool_calls": tcs}
                    reasoning = get_reasoning_for_call(tcs[0]["id"]) if tcs else None
                    if reasoning is not None:
                        msg["reasoning_content"] = reasoning
                        print(f"[REASONING] injected {len(reasoning)} chars into assistant msg with {len(tcs)} tool_calls")
                    messages.append(msg)

            elif item_type == "function_call_output":
                messages.append({
                    "role": "tool",
                    "tool_call_id": item.get("call_id", ""),
                    "content": str(item.get("output", "")),
                })
                i += 1

            elif "role" in item:
                messages.append({"role": item.get("role", "user"), "content": item.get("content", "")})
                i += 1
            else:
                messages.append({"role": "user", "content": json.dumps(item)})
                i += 1

    chat["messages"] = messages

    # Validate: every assistant msg with tool_calls must be followed by enough tool msgs
    for idx, m in enumerate(messages):
        if m.get("role") == "assistant" and m.get("tool_calls"):
            tc_ids = {tc["id"] for tc in m["tool_calls"] if tc.get("id")}
            tool_ids_found = set()
            for j in range(idx + 1, len(messages)):
                nxt = messages[j]
                if nxt.get("role") != "tool":
                    break
                tool_ids_found.add(nxt.get("tool_call_id", ""))
            missing = tc_ids - tool_ids_found
            if missing:
                print(f"[CONVERTER] BAD MSG STRUCTURE: assistant[{idx}] has {len(tc_ids)} tool_calls but missing tool msgs for {missing}")
                print(f"[CONVERTER] input items dump:")
                for k, item in enumerate(inp):
                    t = item.get("type", "?") if isinstance(item, dict) else "non-dict"
                    cid = item.get("call_id", "") if isinstance(item, dict) else ""
                    print(f"[CONVERTER]   [{k}] type={t} call_id={cid}")
                break

    tools = filter_tools(body.get("tools"))
    if tools:
        chat["tools"] = tools
        chat["tool_choice"] = body.get("tool_choice", "auto")

    if "max_output_tokens" in body:
        chat["max_tokens"] = body["max_output_tokens"]
    if "temperature" in body:
        chat["temperature"] = body["temperature"]
    if "top_p" in body:
        chat["top_p"] = body["top_p"]

    chat["stream"] = True
    return chat
