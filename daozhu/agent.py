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
from .chat_service import call_llm_simple

logger = logging.getLogger(__name__)

# 确保工具已注册
from .tools import workspace_tools  # noqa: F401
from .tools import template_tools  # noqa: F401
from .tools import file_tools  # noqa: F401
from .tools import workspace_api_tools  # noqa: F401
from .tools import web_search_tool  # noqa: F401
from .tools import browser_tool  # noqa: F401

MAX_ITERATIONS = 99

# 模块导入
from .agent_context import build_dynamic_context
from .prompts import SYSTEM_PROMPT
from .agent_intent import classify_intent
from .agent_planner import make_plan, format_plan_for_context, replan
from .agent_solver import (
    verify_solved, build_retry_hint,
    evaluate_gate, evaluate_progress,
    GateResult, ProgressResult,
)
from .agent_protocol import (
    build_anthropic_headers as _build_anthropic_headers,
    convert_openai_tools_to_anthropic as _convert_openai_tools_to_anthropic,
    convert_messages_for_anthropic as _convert_messages_for_anthropic,
    parse_anthropic_response as _parse_anthropic_response,
)
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

    # === 前缀缓存优化 ===
    system_content = SYSTEM_PROMPT

    # 动态上下文（工作区列表 + 记忆 + 统计）
    context_parts = build_dynamic_context(memory_context)
    full_messages = [{"role": "system", "content": system_content}]
    if context_parts:
        full_messages.append({
            "role": "system",
            "content": "\n\n".join(context_parts),
        })
    full_messages.extend(messages)

    # === 意图识别 + 规划 ===
    _user_msg = ""
    _recent_context = ""
    for m in reversed(messages):
        if m.get("role") == "user" and not _user_msg:
            content = m.get("content", "")
            if isinstance(content, str):
                _user_msg = content
            break

    # 收集最近 3 轮对话作为上下文
    _context_turns = []
    for m in messages[-6:]:  # 最近 6 条消息（约 3 轮）
        role = m.get("role", "")
        content = m.get("content", "")
        if role in ("user", "assistant") and isinstance(content, str) and content:
            _context_turns.append(f"{role}: {content[:100]}")
    if len(_context_turns) > 1:
        _recent_context = "\n".join(_context_turns[:-1])  # 排除最新这条

    # 意图分类
    _intent = await classify_intent(_user_msg, _recent_context)

    if _intent["type"] == "ambiguous":
        # 追问用户
        clarification = _intent.get("clarification", "能说得更具体一些吗？")
        yield clarification
        return

    if _intent["type"] == "simple_chat":
        # 纯对话：不给工具，直接流式对话 → 过统一输出闸门（#082 AC1/AC2）
        try:
            # 构建 headers（simple_chat 也需要）
            if protocol == "anthropic":
                headers = _build_anthropic_headers(api_key)
            else:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

            # 先获取完整回复（需要过闸门评估）
            response_text = ""
            async for chunk in _stream_final_response(
                base_url, headers, model, full_messages, protocol
            ):
                response_text += chunk

            if not response_text:
                response_text = "你好！有什么我可以帮你的吗？"

            # 统一输出闸门（AC1）
            gate_result = await evaluate_gate(
                user_question=_user_msg,
                response=response_text,
                intent_type="simple_chat",
            )

            if gate_result.needs_escalation:
                # 误分类自修正（AC1）：切换到 needs_action
                logger.info("[Gate] simple_chat 需要升级到 needs_action")
                _intent["type"] = "needs_action"
                _intent["goal"] = _intent.get("goal", _user_msg[:80])
                _intent["solved_when"] = "完成用户请求"
                # 不 return，继续往下走 needs_action 路径
            elif not gate_result.quality_ok:
                # 质量不足 → Reflect-Refine（AC2）
                from .agent_verifier import verify_and_refine
                from .agent_models import ExecutionRecord
                empty_record = ExecutionRecord(had_tool_calls=False)
                refined = await verify_and_refine(
                    output=response_text,
                    record=empty_record,
                    user_question=_user_msg,
                    llm_call_fn=lambda p: call_llm_simple(p, max_tokens=300),
                )
                yield refined
                return
            else:
                # 通过闸门 → 直接输出
                yield response_text
                return

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

    # === 继续执行流程 ===
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
    _consecutive_failures = {}
    _had_tool_calls = False
    _tool_exec_results = []
    _tool_full_results = []
    _usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "cache_hit_tokens": 0}
    _retry_attempted = False  # #081: fallback 重试标记

    # Guardrail 控制器
    from .agent_guardrails import ToolGuardrailController, ProgressTrend, RelevanceGate
    _guardrails = ToolGuardrailController()
    _progress_trend = ProgressTrend()
    _relevance_gate = RelevanceGate()
    _budget_multiplier = 1  # 加速消耗时增大

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
                    from .agent_executor import execute_tool
                    for tool_call in tool_calls:
                        func = tool_call["function"]
                        tool_name = func["name"]
                        try:
                            tool_args = json.loads(func.get("arguments", "{}"))
                        except json.JSONDecodeError:
                            tool_args = {}

                        # 执行工具（含权限/guardrails/日志/失败检测）
                        exec_result, result, markers = await execute_tool(
                            tool_name=tool_name,
                            tool_args=tool_args,
                            tool_call_id=tool_call["id"],
                            plan_tools=_plan.get("tools_needed", []),
                            guardrails=_guardrails,
                            relevance_gate=_relevance_gate,
                            consecutive_failures=_consecutive_failures,
                            protocol=protocol,
                        )

                        # 推送前端标记
                        for marker in markers:
                            yield marker

                        # 收集结果摘要
                        if exec_result.denied:
                            _tool_exec_results.append(f"🚫 {tool_name}: 权限拒绝")
                        elif exec_result.blocked:
                            _tool_exec_results.append(f"🛑 {tool_name}: 被阻断")
                        elif exec_result.success:
                            _tool_exec_results.append(f"✅ {tool_name}: 成功")
                        else:
                            _tool_exec_results.append(f"❌ {tool_name}: 失败")

                        _tool_full_results.append({
                            "name": tool_name,
                            "success": exec_result.success,
                            "error": exec_result.error,
                            "result": exec_result.result,
                        })

                        # 添加工具结果到消息
                        if protocol == "anthropic":
                            full_messages.append({
                                "role": "user",
                                "content": [{"type": "tool_result", "tool_use_id": tool_call["id"], "content": result}],
                            })
                        else:
                            full_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": result,
                            })

                    # 继续循环，让 LLM 处理工具结果
                    # 会话压缩检测
                    from .compaction import should_compact, compact_messages
                    if should_compact(full_messages):
                        full_messages = await compact_messages(full_messages, conversation_id)

                    # ─── #082: 每轮控制论回调（进展评估 + 趋势 + 递进响应）───
                    from .agent_solver import post_iteration_evaluate
                    _feedback = await post_iteration_evaluate(
                        plan=_plan,
                        tool_results=_tool_full_results,
                        progress_trend=_progress_trend,
                        relevance_gate=_relevance_gate,
                    )

                    # 推送前端标记
                    for _marker in _feedback.yield_markers:
                        yield _marker

                    # 注入消息
                    for _msg in _feedback.inject_messages:
                        full_messages.append(_msg)

                    # 重规划
                    if _feedback.new_plan:
                        _plan = _feedback.new_plan
                        logger.info("[Trend] 重规划完成")

                    # 加速消耗
                    _budget_multiplier = _feedback.budget_multiplier

                    # 日志记录（AC13）
                    logger.info(
                        f"[Loop] iteration={iteration}, scores={_progress_trend.scores[-3:]}, "
                        f"stall={_progress_trend.stall_count}, multiplier={_budget_multiplier}"
                    )

                    # 加速消耗 budget（AC8）
                    iteration += (_budget_multiplier - 1)

                    continue

                else:
                    # 没有工具调用，输出最终响应
                    final_content = message.get("content", "")

                    # === #081: 目标驱动验证 ===
                    if _had_tool_calls:
                        from .agent_models import ExecutionRecord, ToolCall
                        from .agent_responder import generate_response

                        # 构建 ExecutionRecord
                        exec_record = ExecutionRecord(had_tool_calls=True)
                        for item in _tool_full_results:
                            tc = ToolCall(
                                tool_name=item["name"],
                                success=item["success"],
                                error=item.get("error", ""),
                                result=item.get("result", ""),
                            )
                            exec_record.tool_calls.append(tc)

                        # 目标验证：问题解决了吗？（#081）
                        _solved_when = _intent.get("solved_when", "")
                        _is_solved = await verify_solved(exec_record, _solved_when)

                        if not _is_solved and not _retry_attempted:
                            # 未解决 + 还没重试过 → 注入 fallback 提示，继续循环
                            _retry_attempted = True
                            retry_hint = build_retry_hint(_plan, exec_record)
                            full_messages.append({
                                "role": "user",
                                "content": retry_hint,
                            })
                            logger.info("[Solver] 目标未达成，触发重试")
                            # 重置工具结果以收集重试结果
                            _tool_full_results = []
                            _tool_exec_results = []
                            continue  # 回到 while 循环重试

                        # 已解决或已重试过 → 生成最终回复
                        user_q = ""
                        for m in reversed(full_messages):
                            if m.get("role") == "user":
                                content = m.get("content", "")
                                if isinstance(content, str) and not content.startswith("[系统提示"):
                                    user_q = content[:200]
                                    break

                        try:
                            verified_response = await generate_response(
                                user_question=user_q,
                                record=exec_record,
                                final_content=final_content,
                            )
                            yield verified_response
                            yield f"[USAGE:{json.dumps(_usage_total)}]"
                            return
                        except Exception:
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
