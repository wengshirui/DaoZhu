"""
岛主 DaoZhu — 平台级 AI Agent
参考: Hermes-Agent AIAgent.run_conversation() 对话循环
职责: 接收用户消息 → 调用 LLM → 工具调用循环 → 返回最终响应
"""

import json
import logging
from typing import AsyncGenerator

import httpx

from .config import get_config_value, get_api_key
from .tools.registry import registry
from .memory_service import build_memory_context
from .skill_loader import get_skills_summary

logger = logging.getLogger(__name__)

# 确保工具已注册
from .tools import workspace_tools  # noqa: F401
from .tools import template_tools  # noqa: F401
from .tools import file_tools  # noqa: F401

MAX_ITERATIONS = 10  # 工具调用最大循环次数

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
- 当需要操作工作区时，使用提供的工具函数

重要：当用户询问工作区状态或要求启停工作区时，使用工具来执行操作，不要凭空回答。
"""


async def agent_chat_stream(
    messages: list[dict],
    memory_context: str = "",
) -> AsyncGenerator[str, None]:
    """
    Agent 对话循环（流式版本）
    实现: LLM 调用 → 检查 tool_calls → 执行工具 → 循环 → 最终文本响应流式输出

    参考 Hermes-Agent 的 run_conversation() 循环:
    while iterations < max:
        response = LLM(messages, tools)
        if tool_calls: execute → append result → continue
        else: return response.content
    """
    provider = get_config_value("ai.provider", "deepseek")
    model = get_config_value("ai.model", "deepseek-chat")
    api_key = get_api_key(provider)
    base_url = get_config_value("ai.base_url", "https://api.deepseek.com/v1")

    if not api_key:
        yield "⚠️ 未配置 AI API Key。请在 .env 文件中设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY。"
        return

    # 构建 system prompt（含记忆 + 技能）
    system_content = SYSTEM_PROMPT
    skills_summary = get_skills_summary()
    if skills_summary:
        system_content += "\n\n" + skills_summary
    if memory_context:
        system_content += "\n\n" + memory_context

    # 构建完整消息列表
    full_messages = [{"role": "system", "content": system_content}] + messages

    # 获取工具 schema
    tool_schemas = registry.get_schemas()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    iteration = 0

    while iteration < MAX_ITERATIONS:
        iteration += 1

        # 非流式调用（工具循环阶段）
        payload = {
            "model": model,
            "messages": full_messages,
            "max_tokens": 2048,
        }

        # 只在有工具时传 tools 参数
        if tool_schemas:
            payload["tools"] = tool_schemas
            payload["tool_choice"] = "auto"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

                if resp.status_code != 200:
                    yield f"⚠️ API 请求失败 (HTTP {resp.status_code})"
                    return

                data = resp.json()
                choice = data["choices"][0]
                message = choice["message"]

                # 检查是否有工具调用
                tool_calls = message.get("tool_calls")

                if tool_calls:
                    # 添加 assistant 消息（含 tool_calls）
                    full_messages.append(message)

                    # 执行每个工具调用
                    for tool_call in tool_calls:
                        func = tool_call["function"]
                        tool_name = func["name"]
                        try:
                            tool_args = json.loads(func.get("arguments", "{}"))
                        except json.JSONDecodeError:
                            tool_args = {}

                        logger.info(f"🔧 调用工具: {tool_name}({tool_args})")

                        # 通知前端（通过 yield 特殊标记）
                        yield f"[TOOL:{tool_name}]"

                        # 执行工具
                        result = await registry.dispatch(tool_name, tool_args)

                        # 添加工具结果到消息
                        full_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result,
                        })

                    # 继续循环，让 LLM 处理工具结果
                    continue

                else:
                    # 没有工具调用，流式输出最终响应
                    final_content = message.get("content", "")
                    if final_content:
                        # 重新用流式请求获取最终响应（更好的用户体验）
                        async for chunk in _stream_final_response(
                            base_url, headers, model, full_messages
                        ):
                            yield chunk
                    return

        except httpx.ConnectError:
            yield "⚠️ 无法连接到 AI 服务，请检查网络。"
            return
        except httpx.ReadTimeout:
            yield "⚠️ AI 服务响应超时。"
            return
        except Exception as e:
            yield f"⚠️ 发生错误: {str(e)}"
            return

    yield "⚠️ 工具调用次数超过上限，请简化你的请求。"


async def _stream_final_response(
    base_url: str, headers: dict, model: str, messages: list[dict]
) -> AsyncGenerator[str, None]:
    """流式输出最终响应（无工具调用时）"""
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "max_tokens": 2048,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST", f"{base_url}/chat/completions",
                headers=headers, json=payload,
            ) as response:
                if response.status_code != 200:
                    yield "⚠️ 流式响应失败"
                    return

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
