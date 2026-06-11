"""
岛主 DaoZhu — 工具执行器（#082 从 agent.py 拆分）
职责：执行单个工具调用，处理权限/guardrails/日志/失败检测

从 agent.py 主循环中提取，保持主循环精简。
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

from .tools.registry import registry
from .tool_log_db import log_tool_call

logger = logging.getLogger(__name__)


@dataclass
class ToolExecResult:
    """单个工具执行的完整结果"""
    tool_name: str
    success: bool
    result: str = ""
    error: str = ""
    duration_ms: int = 0
    blocked: bool = False
    denied: bool = False


async def execute_tool(
    tool_name: str,
    tool_args: dict,
    tool_call_id: str,
    plan_tools: list[str],
    guardrails,
    relevance_gate,
    consecutive_failures: dict,
    protocol: str,
) -> tuple[ToolExecResult, str, list[str]]:
    """
    执行单个工具调用，含权限检查、guardrails、日志、失败检测。

    Returns:
        (exec_result, result_json, yield_markers)
        - exec_result: 结构化结果
        - result_json: 给 LLM 的 JSON 字符串结果
        - yield_markers: 需要 yield 给前端的标记列表
    """
    markers = []
    markers.append(f"[TOOL:{tool_name}]")

    # Permission Gate
    from .permission import check_permission
    permission = check_permission(tool_name, tool_args)
    if permission == "deny":
        result_json = json.dumps({
            "error": f"权限拒绝: 工具 {tool_name} 的此调用被安全规则禁止。",
            "permission": "denied",
        }, ensure_ascii=False)
        markers.append(f"[TOOL_ERR:{tool_name}:权限拒绝]")
        return (
            ToolExecResult(tool_name=tool_name, success=False, error="权限拒绝", denied=True),
            result_json,
            markers,
        )

    # Guardrail 前置检查
    guard_decision = guardrails.before_call(tool_name, tool_args)
    if guard_decision.should_block:
        result_json = json.dumps({"error": guard_decision.message}, ensure_ascii=False)
        markers.append(f"[TOOL_ERR:{tool_name}:{guard_decision.message[:50]}]")
        return (
            ToolExecResult(tool_name=tool_name, success=False, error=guard_decision.message, blocked=True),
            result_json,
            markers,
        )

    # 相关性门控（#082 AC10）
    rel_decision = relevance_gate.check(tool_name, plan_tools)
    if rel_decision.action == "warn":
        logger.info(f"[Relevance] {rel_decision.message}")

    # 执行工具（计时）
    t0 = time.time()
    result_json = await registry.dispatch(tool_name, tool_args)
    duration_ms = int((time.time() - t0) * 1000)

    # 判断成功/失败
    tool_success = True
    tool_error = None
    try:
        r = json.loads(result_json)
        if isinstance(r, dict) and r.get("error"):
            tool_success = False
            tool_error = r["error"][:200]
    except (json.JSONDecodeError, TypeError):
        pass

    # 日志记录
    try:
        log_tool_call(
            tool_name=tool_name,
            args=tool_args,
            result=result_json[:3000] if result_json else "",
            success=tool_success,
            duration_ms=duration_ms,
            error=tool_error,
        )
    except Exception:
        pass

    # 连续失败检测 + knowledge 记录
    if not tool_success:
        consecutive_failures[tool_name] = consecutive_failures.get(tool_name, 0) + 1

        from .memory_db import add_knowledge
        add_knowledge(
            category="tool_failure",
            title=f"{tool_name} 调用失败",
            content=f"错误: {tool_error or '未知'}",
            keywords=tool_name,
        )

        if consecutive_failures[tool_name] >= 2:
            result_json = json.dumps({
                "error": tool_error or "未知错误",
                "hint": f"工具 {tool_name} 已连续失败 {consecutive_failures[tool_name]} 次。请换一种方式完成任务。"
            }, ensure_ascii=False)
    else:
        consecutive_failures[tool_name] = 0

    # 前端标记
    if tool_success:
        markers.append(f"[TOOL_OK:{tool_name}]")
    else:
        markers.append(f"[TOOL_ERR:{tool_name}:{(tool_error or '失败')[:50]}]")

    # Guardrail 后置记录
    guard_after = guardrails.after_call(tool_name, tool_args, result_json or "", failed=not tool_success)

    # 相关性 warn 附加到结果
    warn_suffix = ""
    if rel_decision.action == "warn":
        warn_suffix = f"\n\n[⚠️ 此工具不在执行计划中: {rel_decision.message}]"
    if guard_after.action == "warn":
        warn_suffix += f"\n\n[⚠️ Guardrail: {guard_after.message}]"

    if warn_suffix:
        result_json = (result_json or "") + warn_suffix

    return (
        ToolExecResult(
            tool_name=tool_name,
            success=tool_success,
            result=result_json[:2000] if tool_success else "",
            error=tool_error or "",
            duration_ms=duration_ms,
        ),
        result_json,
        markers,
    )
