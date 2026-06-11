"""
岛主 DaoZhu — 统一输出评估器（#082 工程控制论升级）
所有路径的输出都经过此模块评估，无例外。

三种评估模式：
1. 输出闸门评估（所有路径）：answered? quality? needs_escalation?
2. 进展评估（needs_action 循环内）：步骤完成度 → progress_score
3. 最终评估（needs_action 结束时）：目标是否达成 + 质量

设计原则：
- solver 输出 progress_score（位置）
- guardrails 看趋势（速度/方向）
- 评估失败时退化到当前行为，不阻塞执行
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from .chat_service import call_llm_simple
from .agent_models import ExecutionRecord

logger = logging.getLogger(__name__)


# ─── 数据结构 ───────────────────────────────────────────────

@dataclass
class GateResult:
    """统一输出闸门的评估结果"""
    passed: bool = True
    answered: bool = True
    quality_ok: bool = True
    needs_escalation: bool = False
    reason: str = ""


@dataclass
class ProgressResult:
    """每轮进展评估结果"""
    completed: list[str] = field(default_factory=list)
    partial: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    score: float = 0.0
    evaluation_failed: bool = False


# ─── 统一输出闸门（所有路径共用）───────────────────────────

GATE_PROMPT = """评估下面的 AI 回复是否合格。只输出 JSON。

用户问题：{question}
AI 回复：{response}

评估维度：
1. answered: 回复是否实际回答了用户的问题（不是闪烁其词、不是"我不知道"）
2. quality_ok: 回复质量是否达标（信息准确、不冗余、不跑题）
3. needs_escalation: 这个问题是否其实需要查询数据/调用工具才能正确回答

输出格式（严格 JSON）：
{{"answered": true, "quality_ok": true, "needs_escalation": false, "reason": ""}}

规则：
- 打招呼/感谢/告别类回复：answered=true, quality_ok=true, needs_escalation=false
- 回复中说"我不确定/需要查一下"：answered=false, needs_escalation=true
- 回复偏题或信息不完整：quality_ok=false
- reason 只在不合格时填写，一句话说明"""


async def evaluate_gate(
    user_question: str,
    response: str,
    intent_type: str = "simple_chat",
) -> GateResult:
    """
    统一输出闸门：评估回复是否可以输出给用户。
    所有路径（simple_chat / needs_action）的输出都经过此评估。

    Returns:
        GateResult — passed=True 表示可以输出
    """
    # 快速放行：极短的社交互动不需要 LLM 评估
    stripped_q = user_question.strip()
    if len(stripped_q) <= 4 and any(
        w in stripped_q for w in ("你好", "hi", "嗨", "谢谢", "拜拜", "好的", "ok")
    ):
        return GateResult(passed=True)

    # 快速放行：回复足够长且没有"不确定"信号
    uncertainty_signals = ["我不确定", "需要查", "无法确认", "我不知道", "帮你搜索"]
    has_uncertainty = any(s in response for s in uncertainty_signals)
    if not has_uncertainty and len(response) > 50 and intent_type == "simple_chat":
        # 对 simple_chat 的长回复，代码级快速放行
        return GateResult(passed=True)

    # LLM 评估
    prompt = GATE_PROMPT.format(
        question=user_question[:200],
        response=response[:500],
    )

    try:
        raw = await call_llm_simple(prompt, max_tokens=100)
        if not raw:
            # LLM 调用失败 → 退化放行（AC14）
            logger.warning("[Gate] LLM 调用失败，退化放行")
            return GateResult(passed=True)

        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        result = json.loads(text)

        answered = result.get("answered", True)
        quality_ok = result.get("quality_ok", True)
        needs_escalation = result.get("needs_escalation", False)
        reason = result.get("reason", "")

        passed = answered and quality_ok and not needs_escalation
        logger.info(
            f"[Gate] answered={answered}, quality={quality_ok}, "
            f"escalation={needs_escalation}, passed={passed}"
        )

        return GateResult(
            passed=passed,
            answered=answered,
            quality_ok=quality_ok,
            needs_escalation=needs_escalation,
            reason=reason,
        )

    except (json.JSONDecodeError, TypeError, KeyError) as e:
        logger.warning(f"[Gate] 解析失败: {e}, 退化放行")
        return GateResult(passed=True)
    except Exception as e:
        logger.warning(f"[Gate] 异常: {e}, 退化放行")
        return GateResult(passed=True)


# ─── 进展评估（needs_action 循环内）──────────────────────────

PROGRESS_PROMPT = """判断当前执行进度。只输出 JSON。

执行计划步骤：
{steps}

本轮工具执行结果：
{results}

判断每个步骤的状态：completed（已完成）/ partial（部分完成）/ pending（未开始）

输出格式（严格 JSON）：
{{"completed": ["步骤1"], "partial": ["步骤2"], "pending": ["步骤3"]}}"""


async def evaluate_progress(
    plan: dict,
    record: ExecutionRecord,
    tools_needed: list[str] = None,
) -> ProgressResult:
    """
    每轮进展评估：基于 plan.steps 判断完成度。

    设计决策 D5/D6：
    - 步骤映射方式计算 progress_score
    - 代码级能判定时跳过 LLM（AC5）

    Args:
        plan: 执行计划（含 steps 列表）
        record: 本轮工具执行记录
        tools_needed: plan 中的 tools_needed 列表

    Returns:
        ProgressResult — 含 score 和步骤状态
    """
    steps = plan.get("steps", [])
    if not steps:
        return ProgressResult(score=1.0, completed=["直接执行"])

    total = len(steps)

    # 代码级快速判定（AC5）：
    # 全部失败 → score 不涨
    if record.tool_calls and record.success_count == 0:
        logger.info("[Progress] 全部失败，score=0")
        return ProgressResult(
            pending=[s for s in steps],
            score=0.0,
        )

    # 代码级快速判定：有成功且工具在 plan 中 → 代码估算
    if tools_needed and record.tool_calls:
        in_plan_success = sum(
            1 for tc in record.tool_calls
            if tc.success and tc.tool_name in tools_needed
        )
        if in_plan_success > 0 and record.failure_count == 0:
            # 简单估算：成功调用数 / 总步骤数（上限 1.0）
            estimated_score = min(in_plan_success / total, 1.0)
            completed_count = int(estimated_score * total)
            logger.info(
                f"[Progress] 代码估算: {in_plan_success} 成功调用, "
                f"score={estimated_score:.2f}"
            )
            return ProgressResult(
                completed=steps[:completed_count],
                pending=steps[completed_count:],
                score=estimated_score,
            )

    # LLM 语义评估
    steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
    results_text = record.summary_text()[:600]

    prompt = PROGRESS_PROMPT.format(
        steps=steps_text,
        results=results_text,
    )

    try:
        raw = await call_llm_simple(prompt, max_tokens=150)
        if not raw:
            logger.warning("[Progress] LLM 失败，退化")
            return ProgressResult(score=0.0, evaluation_failed=True)

        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        data = json.loads(text)

        completed = data.get("completed", [])
        partial = data.get("partial", [])
        pending = data.get("pending", [])

        # score = completed / total（partial 算 0.5）
        score = (len(completed) + 0.5 * len(partial)) / total if total > 0 else 0.0
        score = min(score, 1.0)

        logger.info(
            f"[Progress] LLM 评估: completed={len(completed)}, "
            f"partial={len(partial)}, pending={len(pending)}, score={score:.2f}"
        )
        return ProgressResult(
            completed=completed,
            partial=partial,
            pending=pending,
            score=score,
        )

    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"[Progress] 解析失败: {e}")
        return ProgressResult(score=0.0, evaluation_failed=True)
    except Exception as e:
        logger.warning(f"[Progress] 异常: {e}")
        return ProgressResult(score=0.0, evaluation_failed=True)


# ─── 最终评估（needs_action 结束时）─────────────────────────

async def verify_solved(record: ExecutionRecord, solved_when: str) -> bool:
    """
    最终验证：问题是否解决了。保留原有逻辑兼容性。

    Args:
        record: 工具执行记录
        solved_when: 解决标准（来自 intent）

    Returns:
        True = 问题已解决
    """
    if not record.tool_calls:
        return False

    # 层 1：全部失败 = 未解决
    if record.success_count == 0:
        logger.info(f"[Solver] 全部 {record.failure_count} 个工具失败，未解决")
        return False

    # 层 2：无明确标准，有成功调用即视为解决
    if not solved_when or solved_when == "完成用户请求":
        return True

    # 层 3：LLM 判断
    summary = record.summary_text()[:500]
    prompt = (
        f"执行结果摘要：\n{summary}\n\n"
        f"解决标准：{solved_when}\n\n"
        f"根据执行结果，问题解决了吗？只回答 yes 或 no。"
    )

    try:
        answer = await call_llm_simple(prompt, max_tokens=10)
        if answer and "yes" in answer.lower():
            logger.info("[Solver] LLM 判定：已解决")
            return True
        logger.info(f"[Solver] LLM 判定：未解决 (answer={answer})")
        return False
    except Exception as e:
        logger.warning(f"[Solver] 异常: {e}, 默认已解决")
        return True  # AC14: 异常时不阻塞


def build_retry_hint(plan: dict, record: ExecutionRecord) -> str:
    """构建重试提示，注入到消息中引导 LLM 换方案。"""
    failed_tools = [tc.tool_name for tc in record.tool_calls if not tc.success]
    errors = record.errors[:2]

    hint_parts = [
        "[系统提示：上一轮执行未达成目标，请尝试替代方案]",
        f"目标: {plan.get('goal', '')}",
    ]

    if failed_tools:
        hint_parts.append(f"失败的工具: {', '.join(failed_tools)}")
    if errors:
        hint_parts.append(f"错误原因: {'; '.join(errors[:2])}")

    fallback = plan.get("fallback", "")
    if fallback and fallback != "诚实告知用户":
        hint_parts.append(f"替代方案: {fallback}")
    else:
        hint_parts.append(
            "替代方案: 考虑用其他工具组合，或换个参数重试。"
            "如果实在无法完成，诚实告诉用户。"
        )

    return "\n".join(hint_parts)


# ─── 每轮循环后的控制论回调（#082 整合）─────────────────────

@dataclass
class IterationFeedback:
    """每轮迭代结束后的控制反馈"""
    progress: ProgressResult
    yield_markers: list[str] = field(default_factory=list)
    inject_messages: list[dict] = field(default_factory=list)
    new_plan: Optional[dict] = None
    budget_multiplier: int = 1


async def post_iteration_evaluate(
    plan: dict,
    tool_results: list[dict],
    progress_trend,  # ProgressTrend instance
    relevance_gate,  # RelevanceGate instance
) -> IterationFeedback:
    """
    每轮工具调用完成后的统一控制论回调。
    整合：进展评估 + 前端标记 + 趋势检测 + 递进响应 + 工具接纳。

    Returns:
        IterationFeedback — 含需要 yield 的标记和需要注入的消息
    """
    from .agent_planner import replan

    feedback = IterationFeedback(progress=ProgressResult())

    if not tool_results:
        return feedback

    # 构建本轮 ExecutionRecord
    record = ExecutionRecord(had_tool_calls=True)
    for item in tool_results:
        from .agent_models import ToolCall as _TC
        record.tool_calls.append(_TC(
            tool_name=item["name"],
            success=item["success"],
            error=item.get("error", ""),
            result=item.get("result", ""),
        ))

    # 进展评估（AC4/AC5）
    progress = await evaluate_progress(
        plan=plan,
        record=record,
        tools_needed=plan.get("tools_needed", []),
    )
    feedback.progress = progress

    if progress.evaluation_failed:
        return feedback

    # 推送前端进展标记（AC6）
    total_steps = len(plan.get("steps", []))
    completed_count = len(progress.completed)
    desc = progress.completed[-1] if progress.completed else "执行中"
    if total_steps > 0:
        feedback.yield_markers.append(
            f"[PROGRESS:{completed_count}/{total_steps}:{desc[:30]}]"
        )

    # 趋势检测（AC7/AC8）
    trend = progress_trend.record(progress.score)

    if trend.action == "warn":
        feedback.inject_messages.append({
            "role": "user",
            "content": f"[系统提示：{trend.message}]",
        })
    elif trend.action == "replan":
        failed = [tc.tool_name for tc in record.tool_calls if not tc.success]
        errors = record.errors[:2]
        new_plan = await replan(
            original_plan=plan,
            completed_steps=progress.completed,
            failed_tools=failed,
            errors=errors,
        )
        if new_plan is not plan:
            feedback.new_plan = new_plan
            from .agent_planner import format_plan_for_context
            plan_text = format_plan_for_context(new_plan)
            feedback.inject_messages.append({
                "role": "system",
                "content": f"[重规划] {plan_text}",
            })
    elif trend.action == "accelerate":
        feedback.budget_multiplier = 3
        feedback.inject_messages.append({
            "role": "user",
            "content": "[系统提示：长时间无进展，请尽快总结已完成的工作或切换策略。]",
        })

    # 接纳计划外工具（AC11）
    prev_score = progress_trend.scores[-2] if len(progress_trend.scores) > 1 else 0
    if progress.score > prev_score:
        for item in tool_results:
            if item["success"] and item["name"] not in plan.get("tools_needed", []):
                relevance_gate.accept_tool(item["name"])

    return feedback
