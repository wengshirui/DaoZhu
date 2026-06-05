"""
岛主 DaoZhu — LLM 协议适配层
职责: OpenAI ↔ Anthropic 格式转换，与业务逻辑无关
"""

import json


def build_anthropic_headers(api_key: str) -> dict:
    return {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }


def convert_openai_tools_to_anthropic(schemas: list[dict]) -> list[dict]:
    """OpenAI tools 格式 → Anthropic tools 格式"""
    result = []
    for s in schemas:
        func = s.get("function", {})
        result.append({
            "name": func.get("name", ""),
            "description": func.get("description", ""),
            "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
        })
    return result


def convert_messages_for_anthropic(messages: list[dict]) -> tuple[str, list[dict]]:
    """将 OpenAI 格式消息转为 Anthropic 格式，返回 (system_text, anthropic_messages)"""
    system_parts = []
    converted = []
    for msg in messages:
        role = msg.get("role")
        if role == "system":
            system_parts.append(msg.get("content", ""))
        elif role == "tool":
            converted.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": msg.get("tool_call_id", ""),
                    "content": msg.get("content", ""),
                }],
            })
        elif role == "assistant" and msg.get("tool_calls"):
            content_blocks = []
            text = msg.get("content") or ""
            if text:
                content_blocks.append({"type": "text", "text": text})
            for tc in msg["tool_calls"]:
                func = tc.get("function", {})
                args_str = func.get("arguments", "{}")
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                except json.JSONDecodeError:
                    args = {}
                content_blocks.append({
                    "type": "tool_use",
                    "id": tc.get("id", ""),
                    "name": func.get("name", ""),
                    "input": args,
                })
            converted.append({"role": "assistant", "content": content_blocks})
        else:
            converted.append({"role": role, "content": msg.get("content", "")})
    return "\n\n".join(system_parts), converted


def parse_anthropic_response(data: dict) -> dict:
    """将 Anthropic 响应归一化为 OpenAI 格式"""
    content_blocks = data.get("content", [])
    text_parts = []
    tool_calls = []
    for block in content_blocks:
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))
        elif block.get("type") == "tool_use":
            tool_calls.append({
                "id": block.get("id", ""),
                "type": "function",
                "function": {
                    "name": block.get("name", ""),
                    "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                },
            })
    message = {"role": "assistant", "content": "\n".join(text_parts) if text_parts else ""}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"message": message}
