"""
岛主 DaoZhu — 流式响应辅助函数
从 agent.py 分离出来以控制文件大小。
"""

import json
from typing import AsyncGenerator

import httpx

from .agent_protocol import (
    convert_messages_for_anthropic as _convert_messages_for_anthropic,
)


async def stream_final_response(
    base_url: str, headers: dict, model: str, messages: list[dict], protocol: str = "openai"
) -> AsyncGenerator[str, None]:
    """流式输出最终响应（无工具调用时）"""
    if protocol == "anthropic":
        sys_text, anthro_msgs = _convert_messages_for_anthropic(messages)
        payload = {
            "model": model,
            "messages": anthro_msgs,
            "max_tokens": 2048,
            "stream": True,
        }
        if sys_text:
            payload["system"] = sys_text
        endpoint = f"{base_url}/v1/messages"
    else:
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "max_tokens": 2048,
        }
        endpoint = f"{base_url}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST", endpoint,
                headers=headers, json=payload,
            ) as response:
                if response.status_code != 200:
                    yield "⚠️ 流式响应失败"
                    return

                if protocol == "anthropic":
                    current_event = ""
                    async for line in response.aiter_lines():
                        if line.startswith("event: "):
                            current_event = line[7:].strip()
                        elif line.startswith("data: "):
                            if current_event == "content_block_delta":
                                try:
                                    chunk = json.loads(line[6:])
                                    delta = chunk.get("delta", {})
                                    if delta.get("type") == "text_delta":
                                        text = delta.get("text", "")
                                        if text:
                                            yield text
                                except json.JSONDecodeError:
                                    pass
                            elif current_event == "message_stop":
                                break
                        elif line == "":
                            current_event = ""
                else:
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            content = chunk["choices"][0].get("delta", {}).get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
    except Exception as e:
        yield f"⚠️ 流式输出错误: {str(e)}"
