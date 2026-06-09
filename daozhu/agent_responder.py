"""
岛主 DaoZhu — Agent 输出生成器（#079 Stage 3）
独立的回复生成阶段：只基于 ExecutionRecord 生成自然语言。

核心设计：这个 LLM 只看到结构化执行结果，看不到工具调用的中间过程。
它没有"可以编造的素材"——要么照着结果说，要么说没有结果。
"""

import logging
from typing import AsyncGenerator

from .agent_models import ExecutionRecord
from .agent_verifier import verify_and_refine
from .chat_service import call_llm_simple

logger = logging.getLogger(__name__)

RESPONDER_PROMPT = """你是回复生成器。根据下面的工具执行结果，给用户生成一句自然语言回复。

规则（🔴 不可违反）：
1. 只引用"执行结果"中存在的数据，不可添加任何未出现的信息
2. 执行成功 → 简洁确认结果
3. 执行失败 → 直接说"XX 失败了：原因"
4. 没有执行任何工具 → 说"我还没有查询"或正常对话回复
5. 不要提及"工具"、"API"、"调用"等技术术语，用用户能理解的语言
6. 语气自然平等，不要用"主人/您"

用户问题：{question}

执行结果：
{execution_summary}

请直接输出给用户的回复："""


async def generate_response(
    user_question: str,
    record: ExecutionRecord,
    final_content: str = "",
) -> str:
    """
    基于执行记录生成回复 + 验证修正。

    策略：
    - 如果 LLM 循环已给出 final_content（有实质内容）→ 直接验证它
    - 如果 final_content 为空/太短 → 用 responder 基于 ExecutionRecord 生成
    """
    # 纯对话（无工具调用）→ 快速路径
    if not record.had_tool_calls and final_content:
        return final_content

    if not record.had_tool_calls:
        return final_content or "我需要更多信息才能帮你。能具体说说想做什么吗？"

    # 有工具调用：判断是否已有实质回复
    has_substantial_content = final_content and len(final_content.strip()) > 20

    if has_substantial_content:
        # LLM 循环已给出回复 → 只做验证（不重新生成）
        verified = await verify_and_refine(
            output=final_content.strip(),
            record=record,
            user_question=user_question,
            llm_call_fn=lambda p: call_llm_simple(p, max_tokens=300),
        )
        return verified

    # final_content 为空或太短 → 用 responder 基于执行结果生成
    prompt = RESPONDER_PROMPT.format(
        question=user_question[:200],
        execution_summary=record.summary_text(),
    )
    response = await call_llm_simple(prompt, max_tokens=500)

    if response:
        verified = await verify_and_refine(
            output=response.strip(),
            record=record,
            user_question=user_question,
            llm_call_fn=lambda p: call_llm_simple(p, max_tokens=300),
        )
        return verified
    else:
        # LLM 调用失败 → 代码兜底
        from .agent_verifier import generate_safe_fallback
        return generate_safe_fallback(record)
