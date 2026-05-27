"""
岛主 DaoZhu — AI 对话服务
职责: 调用 LLM API，流式返回响应
"""

import json
from typing import AsyncGenerator

import httpx

from .config import get_config_value, get_api_key, get_provider_base_url, get_provider_model, get_provider_protocol


SYSTEM_PROMPT = """你是岛主平台的管家。你帮助用户管理他们的数字岛屿。

你的能力：
- 帮用户建造新的工作区（待办、记账、笔记等应用）
- 管理已有工作区（启动、停止、查看状态）
- 回答关于平台使用的问题

你的风格：
- 简洁友好，像一个贴心的管家
- 用中文回复
- 如果用户想建造工作区，先确认需求再动手
- 自然地运用你对用户的记忆，不要刻意提及"我记得"
"""


def _convert_messages_for_anthropic(messages: list[dict]) -> tuple[str, list[dict]]:
    """将 OpenAI 格式消息转为 Anthropic 格式，返回 (system_text, anthropic_messages)"""
    system_parts = []
    converted = []
    for msg in messages:
        role = msg.get("role")
        if role == "system":
            system_parts.append(msg.get("content", ""))
        else:
            converted.append({"role": role, "content": msg.get("content", "")})
    return "\n\n".join(system_parts), converted


async def chat_stream(
    messages: list[dict],
    model: str = None,
    provider: str = None,
    memory_context: str = "",
) -> AsyncGenerator[str, None]:
    """
    调用 LLM API 并流式返回内容
    yields: 每个 token/chunk 的文本
    """
    if provider is None:
        provider = get_config_value("ai.provider", "deepseek")
    if model is None:
        model = get_provider_model(provider)

    api_key = get_api_key(provider)
    base_url = get_provider_base_url(provider)
    protocol = get_provider_protocol(provider)

    if not api_key:
        yield "⚠️ 未配置 AI API Key。请在设置页面(⚙️)配置对应的 API Key。"
        return

    # 构建 system prompt（含记忆上下文）
    system_content = SYSTEM_PROMPT
    if memory_context:
        system_content += "\n\n" + memory_context

    # 构建消息列表
    full_messages = [{"role": "system", "content": system_content}] + messages

    # 根据协议构建 headers
    if protocol == "anthropic":
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        sys_text, anthro_msgs = _convert_messages_for_anthropic(full_messages)
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
        headers = {"Content-Type": "application/json"}
        if provider != "ollama":
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "messages": full_messages,
            "stream": True,
            "max_tokens": 2048,
        }
        endpoint = f"{base_url}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                endpoint,
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    yield f"⚠️ API 请求失败 (HTTP {response.status_code}): {error_body.decode()[:200]}"
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
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    except httpx.ConnectError:
        yield "⚠️ 无法连接到 AI 服务，请检查网络或 base_url 配置。"
    except httpx.ReadTimeout:
        yield "⚠️ AI 服务响应超时，请稍后重试。"
    except Exception as e:
        yield f"⚠️ 发生错误: {str(e)}"
