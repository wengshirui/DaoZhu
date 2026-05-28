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
from .config import get_provider_protocol, get_provider_base_url, get_provider_model

logger = logging.getLogger(__name__)

# 确保工具已注册
from .tools import workspace_tools  # noqa: F401
from .tools import template_tools  # noqa: F401
from .tools import file_tools  # noqa: F401
from .tools import workspace_api_tools  # noqa: F401
from .tools import web_search_tool  # noqa: F401
from .tools import browser_tool  # noqa: F401

MAX_ITERATIONS = 10  # 工具调用最大循环次数


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

你的工作方式（严格遵守）：
1. 收到请求后，先在心里规划需要哪些步骤（不要说出来）
2. 按计划依次执行，每步只调用必要的工具
3. 执行完成后给出简洁的结果总结

你的决策逻辑：
1. 一次性问题（天气、翻译、搜索信息）→ 用 web_search 搜索后直接回答，绝不建工作区
2. 重复性需求（每天记账、管理待办）→ 建议或创建工作区
3. 用户明确说"帮我建一个 XX" → 创建工作区

你的风格：
- 简洁友好，用中文回复
- 高效执行，不做多余的工具调用
- 如果工具失败了，换个思路或直接告诉用户

重要规则：
- 🔴 删除类操作必须先确认
- 调用工具必须提供所有 required 参数
- 超出能力范围直接说"我做不到"，不要乱试
"""


# === Anthropic 协议辅助函数 ===

def _build_anthropic_headers(api_key: str) -> dict:
    return {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }


def _convert_openai_tools_to_anthropic(schemas: list[dict]) -> list[dict]:
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


def _convert_messages_for_anthropic(messages: list[dict]) -> tuple[str, list[dict]]:
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


def _parse_anthropic_response(data: dict) -> dict:
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
    model = get_provider_model(provider)
    api_key = get_api_key(provider)
    base_url = get_provider_base_url(provider)
    protocol = get_provider_protocol(provider)


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

    # 根据协议构建 headers
    if protocol == "anthropic":
        headers = _build_anthropic_headers(api_key)
    else:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    iteration = 0
    _consecutive_failures = {}  # 追踪连续失败次数

    while iteration < MAX_ITERATIONS:
        iteration += 1

        # 根据协议构建 payload
        if protocol == "anthropic":
            sys_text, anthro_msgs = _convert_messages_for_anthropic(full_messages)
            payload = {
                "model": model,
                "messages": anthro_msgs,
                "max_tokens": 2048,
                "system": sys_text,
            }
            if tool_schemas:
                payload["tools"] = _convert_openai_tools_to_anthropic(tool_schemas)
                payload["tool_choice"] = {"type": "auto"}
            endpoint = f"{base_url}/v1/messages"
        else:
            payload = {
                "model": model,
                "messages": full_messages,
                "max_tokens": 2048,
            }
            if tool_schemas:
                payload["tools"] = tool_schemas
                payload["tool_choice"] = "auto"
            endpoint = f"{base_url}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                )

                if resp.status_code != 200:
                    yield f"⚠️ API 请求失败 (HTTP {resp.status_code})"
                    return

                data = resp.json()
                if protocol == "anthropic":
                    message = _parse_anthropic_response(data)["message"]
                else:
                    message = data["choices"][0]["message"]

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
                        if protocol == "anthropic":
                            full_messages.append({
                                "role": "user",
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": tool_call["id"],
                                    "content": result,
                                }],
                            })
                        else:
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
                        # 尝试流式重发（更好的用户体验）
                        try:
                            streamed = False
                            async for chunk in _stream_final_response(
                                base_url, headers, model, full_messages, protocol
                            ):
                                streamed = True
                                yield chunk
                            if not streamed:
                                yield final_content
                        except Exception as e:
                            yield final_content
                    return
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

    # 达到上限：让 LLM 总结已完成的工作，而不是直接报错
    # 注入提示让 LLM 给出阶段性总结
    full_messages.append({
        "role": "user",
        "content": "[系统提示：你已执行了较多步骤。请总结目前完成的工作，告诉用户当前进度，并询问是否需要继续。]"
    })

    # 最后一次调用 LLM 获取总结
    try:
        if protocol == "anthropic":
            sys_text, anthro_msgs = _convert_messages_for_anthropic(full_messages)
            payload = {
                "model": model,
                "messages": anthro_msgs,
                "max_tokens": 1024,
                "system": sys_text,
            }
            endpoint = f"{base_url}/v1/messages"
        else:
            payload = {
                "model": model,
                "messages": full_messages,
                "max_tokens": 1024,
            }
            endpoint = f"{base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if protocol == "anthropic":
                    msg = _parse_anthropic_response(data)["message"]
                else:
                    msg = data["choices"][0]["message"]
                content = msg.get("content", "")
                if content:
                    yield content
                    return
    except Exception:
        pass

    yield "⚠️ 执行步骤较多，已暂停。你可以告诉我接下来要做什么，我继续执行。"


async def _stream_final_response(
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
                    # Anthropic SSE: event: xxx\ndata: {json}\n\n
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
                    # OpenAI SSE: data: {json}
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
