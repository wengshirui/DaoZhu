"""
岛主 DaoZhu — 目标验证器（#081）
判断"问题是否真的解决了"，而不只是"回复有没有幻觉"。

两层验证：
1. 代码级：工具是否全失败
2. LLM 判断：solved_when 条件是否满足
"""

import logging

from .chat_service import call_llm_simple
from .agent_models import ExecutionRecord

logger = logging.getLogger(__name__)


async def verify_solved(record: ExecutionRecord, solved_when: str) -> bool:
    """
    验证问题是否解决了。

    Args:
        record: 工具执行记录
        solved_when: 解决标准（来自 intent）

    Returns:
        True = 问题已解决，False = 未解决需重试
    """
    if not record.tool_calls:
        # 没调任何工具 → 未解决
        logger.info("[Solver] 无工具调用，未解决")
        return False

    # 层 1：代码级判断 — 全部失败 = 肯定没解决
    if record.success_count == 0:
        logger.info(
            f"[Solver] 全部 {record.failure_count} 个工具失败，未解决"
        )
        return False

    # 层 2：如果没有明确的 solved_when，有成功的工具调用就算解决
    if not solved_when or solved_when == "完成用户请求":
        logger.info("[Solver] 无明确解决标准，有成功调用即视为解决")
        return True

    # 层 3：轻量 LLM 判断
    summary = record.summary_text()[:500]
    prompt = (
        f"执行结果摘要：\n{summary}\n\n"
        f"解决标准：{solved_when}\n\n"
        f"根据执行结果，问题解决了吗？只回答 yes 或 no。"
    )

    answer = await call_llm_simple(prompt, max_tokens=10)
    if answer and "yes" in answer.lower():
        logger.info("[Solver] LLM 判定：已解决")
        return True

    logger.info(f"[Solver] LLM 判定：未解决 (answer={answer})")
    return False


def build_retry_hint(plan: dict, record: ExecutionRecord) -> str:
    """
    构建重试提示，注入到消息中引导 LLM 换方案。
    """
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
