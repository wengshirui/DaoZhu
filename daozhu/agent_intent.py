"""
岛主 DaoZhu — 意图识别器（#080 Phase 1）
在 agent 动手之前先"想一下"：分析用户要什么、怎样算解决了。

三种分类：
- simple_chat: 纯对话，不需要工具（你好/谢谢/闲聊/知识问答）
- needs_action: 需要调工具解决问题
- ambiguous: 说了要做什么但缺关键信息，需要追问
"""

import json
import logging

from .chat_service import call_llm_simple

logger = logging.getLogger(__name__)

INTENT_PROMPT = """分析用户的消息，判断意图类型。只输出 JSON，不要其他文字。

分类规则：
- simple_chat: 打招呼、闲聊、感谢、告别、纯知识问答（不需要查用户数据）
- needs_action: 需要调用工具才能完成（查待办、建工作区、搜索、操作文件等）
- ambiguous: 用户想做某事但缺少关键信息（如"帮我建个工作区"没说什么类型）

输出格式（严格 JSON）：
{{"type": "simple_chat|needs_action|ambiguous", "goal": "用户想达成什么（一句话）", "solved_when": "怎样才算解决了（一句话，needs_action时必填）", "clarification": "要追问什么（ambiguous时必填，否则空字符串）"}}

用户消息：{message}"""


async def classify_intent(user_message: str) -> dict:
    """
    分析用户意图。返回结构化 intent 字典。
    失败时默认返回 needs_action（宁可多给工具，不可漏掉）。
    """
    # 快速规则：极短消息直接判定
    stripped = user_message.strip()
    if len(stripped) <= 4 and any(
        w in stripped for w in ("你好", "hi", "嗨", "谢谢", "拜拜", "好的", "ok")
    ):
        logger.info(f"[Intent] 规则命中 simple_chat: '{stripped}'")
        return {
            "type": "simple_chat",
            "goal": "打招呼/回应",
            "solved_when": "",
            "clarification": "",
        }

    # LLM 分类
    prompt = INTENT_PROMPT.format(message=user_message[:300])
    raw = await call_llm_simple(prompt, max_tokens=150)

    if not raw:
        logger.warning("[Intent] LLM 调用失败，默认 needs_action")
        return _default_intent(user_message)

    # 解析 JSON
    try:
        # 有时 LLM 会包裹在 ```json ... ``` 中
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        intent = json.loads(text)

        # 校验必须字段
        if intent.get("type") not in ("simple_chat", "needs_action", "ambiguous"):
            logger.warning(f"[Intent] 无效 type: {intent.get('type')}")
            return _default_intent(user_message)

        intent.setdefault("goal", user_message[:50])
        intent.setdefault("solved_when", "")
        intent.setdefault("clarification", "")

        logger.info(f"[Intent] {intent['type']}: {intent['goal'][:60]}")
        return intent

    except (json.JSONDecodeError, TypeError, KeyError) as e:
        logger.warning(f"[Intent] JSON 解析失败: {e}, raw={raw[:100]}")
        return _default_intent(user_message)


def _default_intent(user_message: str) -> dict:
    """兜底：默认当作 needs_action（宁可多给工具）"""
    return {
        "type": "needs_action",
        "goal": user_message[:80],
        "solved_when": "完成用户请求",
        "clarification": "",
    }
