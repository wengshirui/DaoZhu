"""
岛主 DaoZhu — Agent 后置验证器（#079 Stage 4）
代码级验证 + Reflect-Refine 循环。
参考：hermes-agent file_mutation_verifier + Reflexion + AWS Evaluator

核心原则：代码级验证 > prompt 约束。不信任 LLM，用代码比对事实。
"""

import re
import logging
from typing import Optional

from .agent_models import ExecutionRecord

logger = logging.getLogger(__name__)

MAX_REFLECT_RETRIES = 2


def verify_output(text: str, record: ExecutionRecord) -> Optional[str]:
    """
    代码级验证：比对输出文本 vs 执行记录。
    返回问题描述（如有），或 None 表示通过。
    """
    if not text or not record.had_tool_calls:
        return None  # 纯对话不验证

    issues = []

    # 检查 1：回复中的数字是否来自工具返回
    numbers_in_text = set()
    for match in re.finditer(r'\b(\d+)\b', text):
        n = int(match.group(1))
        if 2 <= n <= 100000:
            numbers_in_text.add(n)

    numbers_in_results = record.numbers_in_results()
    # 允许的数字：来自结果中的 + 常见的小数字(2-10)
    suspicious_numbers = numbers_in_text - numbers_in_results - set(range(2, 11))
    if suspicious_numbers:
        issues.append(
            f"回复中的数字 {suspicious_numbers} 未在工具返回中找到。"
            f"工具返回中的数字有: {numbers_in_results or '无'}"
        )

    # 检查 2：有工具失败但回复声称成功
    claim_success_words = ["已完成", "已帮你", "成功", "已经做了", "搞定"]
    if record.failure_count > 0:
        for word in claim_success_words:
            if word in text:
                failed_tools = [tc.tool_name for tc in record.tool_calls if not tc.success]
                issues.append(
                    f"回复声称'{word}'，但以下工具执行失败: {', '.join(failed_tools)}。"
                    f"失败原因: {'; '.join(record.errors[:3])}"
                )
                break

    # 检查 3：所有工具都失败但回复没有提到失败
    if record.failure_count > 0 and record.success_count == 0:
        failure_words = ["失败", "错误", "没成功", "无法", "不了"]
        has_failure_mention = any(w in text for w in failure_words)
        if not has_failure_mention:
            issues.append(
                f"所有 {record.failure_count} 个工具调用都失败了，"
                f"但回复中没有提到任何失败。失败原因: {'; '.join(record.errors[:3])}"
            )

    if issues:
        return "\n".join(issues)
    return None


def build_correction_prompt(issues: str, record: ExecutionRecord, user_question: str) -> str:
    """构建修正提示（反馈给 LLM 让它重新生成）"""
    return f"""你的上一次回复有以下事实错误：
{issues}

以下是实际的工具执行结果（以此为准，不可编造）：
{record.summary_text()}

用户的原始问题是：{user_question}

请重新生成回复。规则：
- 只引用上面"实际执行结果"中的数据
- 失败的操作必须说失败
- 不要添加执行结果中没有的数字或声明
- 直接输出给用户的回复，不要解释修正过程"""


def generate_safe_fallback(record: ExecutionRecord) -> str:
    """
    代码级安全回复 — 100% 基于执行记录，零幻觉。
    当 LLM 连续修正都失败时使用。
    """
    if not record.tool_calls:
        return "我尝试处理你的请求，但没有执行任何操作。需要我换个方式试试吗？"

    parts = []
    for tc in record.tool_calls:
        if tc.success:
            # 从 result 中提取关键信息
            preview = tc.result[:150].strip() if tc.result else "完成"
            parts.append(f"✅ {tc.tool_name}: {preview}")
        else:
            parts.append(f"❌ {tc.tool_name}: 失败 — {tc.error or '未知原因'}")

    result = "\n".join(parts)
    result += "\n\n⚠️ 此回复由系统验证器生成，确保与实际执行结果一致。"
    return result


async def verify_and_refine(
    output: str,
    record: ExecutionRecord,
    user_question: str,
    llm_call_fn,
) -> str:
    """
    验证 + 修正循环（Reflect-Refine）。

    Args:
        output: LLM 首次生成的回复
        record: 工具执行记录
        user_question: 用户原始问题
        llm_call_fn: async def(prompt) -> str，简单 LLM 调用函数

    Returns:
        验证通过的回复（或代码兜底回复）
    """
    for attempt in range(MAX_REFLECT_RETRIES):
        issues = verify_output(output, record)
        if not issues:
            return output  # 通过验证

        logger.warning(f"验证器发现问题 (attempt {attempt + 1}): {issues[:100]}")

        if attempt < MAX_REFLECT_RETRIES - 1:
            # 反馈修正
            correction_prompt = build_correction_prompt(issues, record, user_question)
            corrected = await llm_call_fn(correction_prompt)
            if corrected:
                output = corrected.strip()
            else:
                break  # LLM 调用失败，直接兜底
        else:
            # 重试耗尽 → 代码兜底
            output = generate_safe_fallback(record)

    return output
