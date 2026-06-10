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
from .config import get_provider_protocol, get_provider_base_url, get_provider_model
from .tool_log_db import log_tool_call

logger = logging.getLogger(__name__)

# 确保工具已注册
from .tools import workspace_tools  # noqa: F401
from .tools import template_tools  # noqa: F401
from .tools import file_tools  # noqa: F401
from .tools import workspace_api_tools  # noqa: F401
from .tools import web_search_tool  # noqa: F401
from .tools import browser_tool  # noqa: F401

MAX_ITERATIONS = 10  # 工具调用最大循环次数


# === Context 构建（从 agent_context.py 导入）===
from .agent_context import build_dynamic_context

# === 系统提示词（从 prompts.py 导入）===
from .prompts import SYSTEM_PROMPT, REVIEWER_PROMPT

# === 意图识别 + 规划（#080）===
from .agent_intent import classify_intent
from .agent_planner import make_plan, format_plan_for_context


# === Anthropic 协议（从 agent_protocol.py 导入）===
from .agent_protocol import (
    build_anthropic_headers as _build_anthropic_headers,
    convert_openai_tools_to_anthropic as _convert_openai_tools_to_anthropic,
    convert_messages_for_anthropic as _convert_messages_for_anthropic,
    parse_anthropic_response as _parse_anthropic_response,
)

# === 流式输出（从 agent_stream.py 导入）===
from .agent_stream import stream_final_response as _stream_final_response


async def agent_chat_stream(
    messages: list[dict],
    memory_context: str = "",
    conversation_id: str = "",
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
    thinking_enabled = get_config_value("ai.thinking", False)


    if not api_key:
        yield "⚠️ 未配置 AI API Key。请在 .env 文件中设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY。"
        return

    # === 前缀缓存优化（参考 Reasonix）===
    # DeepSeek 自动缓存请求前缀（system prompt + tools schema）
    # 只要每轮的前 N 个 token 完全一致，就命中缓存（输入费用降 90%）
    # 因此 system prompt 只放固定内容，动态内容移到 messages 中
    system_content = SYSTEM_PROMPT  # 固定不变的核心指令

    # 动态上下文（工作区列表 + API hint + 记忆 + 统计）
    context_parts = build_dynamic_context(memory_context)

    # 构建完整消息列表：
    # [system(固定)] + [context(动态环境信息)] + [对话历史]
    full_messages = [{"role": "system", "content": system_content}]
    if context_parts:
        full_messages.append({
            "role": "system",
            "content": "\n\n".join(context_parts),
        })
    full_messages.extend(messages)

    # === #080 Phase 1: 意图识别 + 规划 ===
    # 提取用户最新消息用于意图分析
    _user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, str):
                _user_msg = content
            break

    # 意图分类（轻量 LLM call）
    _intent = await classify_intent(_user_msg)

    if _intent["type"] == "ambiguous":
        # 追问用户，不执行任何工具
        clarification = _intent.get("clarification", "能说得更具体一些吗？")
        yield clarification
        return

    if _intent["type"] == "simple_chat":
        # 纯对话：不给工具，直接流式对话
        try:
            async for chunk in _stream_final_response(
                base_url, headers, model, full_messages, protocol
            ):
                yield chunk
        except Exception:
            yield "你好！有什么我可以帮你的吗？"
        return

    # needs_action: 生成执行计划
    _plan = await make_plan(_intent)

    # 将计划注入到上下文中，引导 LLM 有目的地执行
    plan_text = format_plan_for_context(_plan)
    full_messages.append({
        "role": "system",
        "content": plan_text,
    })

    # === 继续原有执行流程 ===

    # 获取工具 schema
    tool_schemas = registry.get_schemas()

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
    _had_tool_calls = False  # 追踪是否有过工具调用
    _tool_exec_results = []  # 收集工具执行结果摘要（#077 防幻觉）
    _tool_full_results = []  # 收集完整工具返回数据（#079 给 responder 用）
    _usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "cache_hit_tokens": 0}

    # Guardrail 控制器（#079 Phase 3）
    from .agent_guardrails import ToolGuardrailController
    _guardrails = ToolGuardrailController()

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
            # 深度思考模式（#075）
            if thinking_enabled and "deepseek" in provider:
                payload["max_tokens"] = 4096  # 思考模式输出更长
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
                # 提取 token 使用量（#061）
                usage = data.get("usage") or {}
                _usage_total["prompt_tokens"] += usage.get("prompt_tokens", 0)
                _usage_total["completion_tokens"] += usage.get("completion_tokens", 0)
                _usage_total["cache_hit_tokens"] += usage.get("prompt_cache_hit_tokens", 0)

                if protocol == "anthropic":
                    message = _parse_anthropic_response(data)["message"]
                else:
                    message = data["choices"][0]["message"]

                # 检查是否有工具调用
                tool_calls = message.get("tool_calls")

                if tool_calls:
                    _had_tool_calls = True
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

                        # === Permission Gate（#060）===
                        from .permission import check_permission
                        permission = check_permission(tool_name, tool_args)
                        if permission == "deny":
                            result = json.dumps({
                                "error": f"权限拒绝: 工具 {tool_name} 的此调用被安全规则禁止。",
                                "permission": "denied",
                            }, ensure_ascii=False)
                            yield f"[TOOL:{tool_name}]"
                            yield f"[TOOL_ERR:{tool_name}:权限拒绝]"
                            _tool_exec_results.append(f"🚫 {tool_name}: 权限拒绝（安全规则禁止）")
                            if protocol == "anthropic":
                                full_messages.append({
                                    "role": "user",
                                    "content": [{"type": "tool_result", "tool_use_id": tool_call["id"], "content": result}],
                                })
                            else:
                                full_messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": result})
                            continue

                        # 通知前端（通过 yield 特殊标记）
                        yield f"[TOOL:{tool_name}]"

                        # Guardrail 前置检查（#079）
                        _guard_decision = _guardrails.before_call(tool_name, tool_args)
                        if _guard_decision.should_block:
                            result = json.dumps({"error": _guard_decision.message}, ensure_ascii=False)
                            yield f"[TOOL_ERR:{tool_name}:{_guard_decision.message[:50]}]"
                            _tool_exec_results.append(f"🛑 {tool_name}: 被阻断 - {_guard_decision.message[:60]}")
                            _tool_full_results.append({"name": tool_name, "success": False, "error": _guard_decision.message, "result": ""})
                            if protocol == "anthropic":
                                full_messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_call["id"], "content": result}]})
                            else:
                                full_messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": result})
                            continue

                        # 执行工具（计时）
                        import time as _time
                        _t0 = _time.time()
                        result = await registry.dispatch(tool_name, tool_args)
                        _duration_ms = int((_time.time() - _t0) * 1000)

                        # 记录到日志
                        _tool_success = True
                        _tool_error = None
                        try:
                            r = json.loads(result)
                            if isinstance(r, dict) and r.get("error"):
                                _tool_success = False
                                _tool_error = r["error"][:200]
                        except (json.JSONDecodeError, TypeError):
                            pass

                        try:
                            log_tool_call(
                                tool_name=tool_name,
                                args=tool_args,
                                result=result[:3000] if result else "",
                                success=_tool_success,
                                duration_ms=_duration_ms,
                                error=_tool_error,
                            )
                        except Exception:
                            pass  # 日志记录不应阻塞主流程

                        # 连续失败检测
                        try:
                            r = json.loads(result)
                            if isinstance(r, dict) and r.get("error"):
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

                        # 推送工具结果状态 + 收集结果摘要（#077）
                        try:
                            r = json.loads(result)
                            if isinstance(r, dict) and r.get("error"):
                                yield f"[TOOL_ERR:{tool_name}:{r['error'][:50]}]"
                                _tool_exec_results.append(f"❌ {tool_name}: 失败 - {r['error'][:60]}")
                                _tool_full_results.append({"name": tool_name, "success": False, "error": r["error"][:200], "result": ""})
                            else:
                                yield f"[TOOL_OK:{tool_name}]"
                                _tool_exec_results.append(f"✅ {tool_name}: 成功")
                                _tool_full_results.append({"name": tool_name, "success": True, "error": "", "result": result[:2000]})
                        except (json.JSONDecodeError, TypeError):
                            yield f"[TOOL_OK:{tool_name}]"
                            _tool_exec_results.append(f"✅ {tool_name}: 成功")
                            _tool_full_results.append({"name": tool_name, "success": True, "error": "", "result": result[:2000]})

                        # Guardrail 后置记录（#079）
                        _is_failed = not _tool_full_results[-1]["success"] if _tool_full_results else False
                        _guard_after = _guardrails.after_call(tool_name, tool_args, result or "", failed=_is_failed)
                        if _guard_after.action == "warn":
                            # 注入警告到工具结果消息中
                            warn_suffix = f"\n\n[⚠️ Guardrail: {_guard_after.message}]"
                            if protocol != "anthropic" and full_messages and full_messages[-1].get("role") == "tool":
                                full_messages[-1]["content"] = full_messages[-1].get("content", "") + warn_suffix

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
                    # === 会话压缩检测（#059）===
                    from .compaction import should_compact, compact_messages
                    if should_compact(full_messages):
                        yield "[COMPACT]"
                        full_messages = await compact_messages(full_messages, conversation_id)

                    continue

                else:
                    # 没有工具调用，输出最终响应
                    final_content = message.get("content", "")

                    # === #079 Pipeline Stage 3+4: 独立输出生成 + 验证 ===
                    if _had_tool_calls:
                        # 有工具调用 → 用独立 responder 基于 ExecutionRecord 生成
                        from .agent_models import ExecutionRecord, ToolCall
                        from .agent_responder import generate_response

                        # 构建 ExecutionRecord（包含完整工具返回数据）
                        exec_record = ExecutionRecord(had_tool_calls=True)
                        for item in _tool_full_results:
                            tc = ToolCall(
                                tool_name=item["name"],
                                success=item["success"],
                                error=item.get("error", ""),
                                result=item.get("result", ""),
                            )
                            exec_record.tool_calls.append(tc)

                        # 提取用户原始问题（从 messages 找最后一个 user）
                        user_q = ""
                        for m in reversed(full_messages):
                            if m.get("role") == "user":
                                content = m.get("content", "")
                                if isinstance(content, str):
                                    user_q = content[:200]
                                break

                        # 调用独立 responder + verifier
                        try:
                            verified_response = await generate_response(
                                user_question=user_q,
                                record=exec_record,
                                final_content=final_content,
                            )
                            yield verified_response
                            yield f"[USAGE:{json.dumps(_usage_total)}]"
                            return
                        except Exception as e:
                            # responder 失败，fallback 到 final_content
                            if final_content:
                                yield final_content
                                yield f"[USAGE:{json.dumps(_usage_total)}]"
                                return

                    # 无工具调用 → 直接输出（纯对话）
                    if final_content:
                        try:
                            streamed = False
                            async for chunk in _stream_final_response(
                                base_url, headers, model, full_messages, protocol
                            ):
                                streamed = True
                                yield chunk
                            if not streamed:
                                yield final_content
                        except Exception:
                            yield final_content
                    yield f"[USAGE:{json.dumps(_usage_total)}]"
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
