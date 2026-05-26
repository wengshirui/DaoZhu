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
from .tools import workspace_api_tools  # noqa: F401
from .tools import web_search_tool  # noqa: F401

MAX_ITERATIONS = 5  # 工具调用最大循环次数（防止乱调浪费 token）


def _get_disabled_tools() -> set:
    """从配置中读取被禁用的工具列表"""
    from .config import get_config_value
    disabled = get_config_value("disabled_tools", [])
    return set(disabled) if disabled else set()


def _build_stats_context() -> str:
    """构建使用统计上下文，触发 AI 主动建议优化"""
    from .memory_db import get_skill_stats, get_stale_skills

    parts = []

    # 工具使用统计
    stats = get_skill_stats()
    if stats:
        # 找出失败率高的
        failing = [s for s in stats if s.get("success_rate", 100) < 70]
        if failing:
            names = ", ".join(s["skill_id"] for s in failing[:3])
            parts.append(f"⚠️ 以下工具最近失败率较高: {names}。如果合适，可以建议用户优化或禁用。")

    # 长期未使用的工具
    stale = get_stale_skills(days=30)
    if stale:
        names = ", ".join(s["skill_id"] for s in stale[:3])
        parts.append(f"💤 以下工具超过30天未使用: {names}。可以建议用户是否需要禁用。")

    if parts:
        return "[以下是资源使用情况，在合适时机自然地提出优化建议：]\n" + "\n".join(parts)
    return ""

SYSTEM_PROMPT = """你是岛主平台的岛管理员。你帮助用户管理他们的数字岛屿。

你的能力：
- 用 web_search 搜索互联网回答一次性问题（天气、新闻、技术问题）
- 帮用户建造新的工作区（待办、记账、笔记等重复使用的应用）
- 管理已有工作区（启动、停止、查看状态）
- 直接操作工作区数据（添加待办、记账等）

你的决策逻辑（严格遵守）：
1. 一次性问题（天气、翻译、搜索信息）→ 用 web_search 搜索后直接回答，绝不建工作区
2. 重复性需求（每天记账、管理待办）→ 建议或创建工作区
3. 用户明确说"帮我建一个 XX" → 创建工作区

你的风格：
- 简洁友好，用中文回复
- 每次最多调用 2-3 个工具就给出回答，不要连续调用很多工具
- 如果第一个工具失败了，换个思路或直接告诉用户

重要规则：
- 🔴 删除类操作必须先确认
- 调用工具必须提供所有 required 参数
- 超出能力范围直接说"我做不到"，不要乱试
- 每次回答前想清楚用哪个工具，不要盲目尝试
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

    # 构建 system prompt（含记忆 + 技能 + 使用统计）
    system_content = SYSTEM_PROMPT
    skills_summary = get_skills_summary()
    if skills_summary:
        system_content += "\n\n" + skills_summary

    # 注入使用统计（触发优化建议）
    stats_context = _build_stats_context()
    if stats_context:
        system_content += "\n\n" + stats_context

    if memory_context:
        system_content += "\n\n" + memory_context

    # 构建完整消息列表
    full_messages = [{"role": "system", "content": system_content}] + messages

    # 获取工具 schema（排除禁用的）
    tool_schemas = registry.get_schemas()
    disabled = _get_disabled_tools()
    if disabled:
        tool_schemas = [t for t in tool_schemas if t["function"]["name"] not in disabled]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    iteration = 0
    _consecutive_failures = {}  # 追踪连续失败次数

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

                        # 连续失败检测
                        try:
                            r = json.loads(result)
                            if r.get("error"):
                                _consecutive_failures[tool_name] = _consecutive_failures.get(tool_name, 0) + 1

                                # 自我优化：记录失败教训到 knowledge
                                from .memory_db import add_knowledge
                                add_knowledge(
                                    category="tool_failure",
                                    title=f"{tool_name} 调用失败",
                                    content=f"错误: {r['error'][:100]}",
                                    keywords=tool_name,
                                )

                                if _consecutive_failures[tool_name] >= 2:
                                    result = json.dumps({
                                        "error": r["error"],
                                        "hint": f"工具 {tool_name} 已连续失败 {_consecutive_failures[tool_name]} 次。请换一种方式完成任务，或直接告诉用户当前遇到的问题。"
                                    }, ensure_ascii=False)
                            else:
                                _consecutive_failures[tool_name] = 0
                        except (json.JSONDecodeError, TypeError):
                            _consecutive_failures[tool_name] = 0

                        # 推送工具结果状态
                        try:
                            r = json.loads(result)
                            if r.get("error"):
                                yield f"[TOOL_ERR:{tool_name}:{r['error'][:50]}]"
                            else:
                                yield f"[TOOL_OK:{tool_name}]"
                        except (json.JSONDecodeError, TypeError):
                            yield f"[TOOL_OK:{tool_name}]"

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
