"""
岛主 DaoZhu — 记忆服务
职责: 从对话中提取记忆 + 在对话前注入相关记忆
参考: Hermes-Agent 分层记忆 + OpenClaw 自动注入
"""

import json
import re
from typing import Optional

from .config import get_config_value, get_api_key
from .memory_db import (
    get_all_profiles, set_profile, search_knowledge,
    add_knowledge, get_recent_knowledge,
)


# === 记忆注入（对话前）===

def build_memory_context(user_message: str) -> str:
    """
    构建记忆上下文，注入到 system prompt 中。
    在每次对话前调用，将相关记忆提供给 LLM。
    """
    parts = []

    # 1. 用户画像
    profiles = get_all_profiles()
    if profiles:
        profile_text = "\n".join(f"- {p['key']}: {p['value']}" for p in profiles[:10])
        parts.append(f"## 用户画像\n{profile_text}")

    # 2. 相关知识检索（基于用户消息关键词）
    keywords = _extract_search_terms(user_message)
    if keywords:
        results = search_knowledge(keywords, limit=3)
        if results:
            knowledge_text = "\n".join(
                f"- [{r['category']}] {r['title']}: {r['content'][:150]}"
                for r in results
            )
            parts.append(f"## 相关记忆\n{knowledge_text}")

    if not parts:
        return ""

    return "\n\n".join(["[以下是你对这位用户的记忆，请自然地运用：]"] + parts)


def _extract_search_terms(text: str) -> str:
    """从用户消息中提取搜索关键词"""
    # 去掉常见停用词，保留有意义的词
    stop_words = {"帮我", "请", "一个", "的", "了", "吗", "呢", "吧", "是", "在",
                  "有", "我", "你", "他", "她", "它", "这", "那", "什么", "怎么",
                  "可以", "能", "要", "想", "做", "用", "和", "或", "但"}
    words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text)
    meaningful = [w for w in words if w not in stop_words and len(w) > 1]
    return " OR ".join(meaningful[:5]) if meaningful else ""


# === 记忆提取（对话后）===

EXTRACT_PROMPT = """分析以下对话，提取需要记住的信息。返回 JSON 格式：

{
  "profiles": [{"key": "偏好类别", "value": "具体偏好"}],
  "knowledge": [{"category": "分类", "title": "标题", "content": "内容", "keywords": "关键词"}]
}

规则：
- profiles: 用户的偏好、习惯、身份信息（如"喜欢暗色主题"、"是程序员"、"常用Python"）
- knowledge: 值得记住的事实或经验（如"用户的记账工作区在7803端口"、"上次创建待办用了Super Productivity参考"）
- 如果没有值得记住的内容，返回空数组
- key 用简短中文描述（如"主题偏好"、"职业"、"常用语言"）

对话内容：
{conversation}

只返回 JSON，不要其他文字。"""


async def extract_memories(messages: list[dict], conversation_id: str = None):
    """
    从对话中提取记忆（异步，在对话结束后调用）
    使用 LLM 分析对话内容，提取用户偏好和知识
    """
    if len(messages) < 2:
        return  # 对话太短，不提取

    # 只取最近的消息（避免 token 过多）
    recent = messages[-10:]
    conversation_text = "\n".join(
        f"{m['role']}: {m['content'][:200]}" for m in recent
    )

    # 调用 LLM 提取
    import httpx
    provider = get_config_value("ai.provider", "deepseek")
    model = get_config_value("ai.model", "deepseek-chat")
    api_key = get_api_key(provider)
    base_url = get_config_value("ai.base_url", "https://api.deepseek.com/v1")

    if not api_key:
        return  # 无 API Key，跳过提取

    prompt = EXTRACT_PROMPT.replace("{conversation}", conversation_text)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.1,
                },
            )

            if resp.status_code != 200:
                return

            data = resp.json()
            content = data["choices"][0]["message"]["content"]

            # 解析 JSON
            result = _parse_extraction(content)
            if not result:
                return

            # 保存提取的记忆
            for profile in result.get("profiles", []):
                if profile.get("key") and profile.get("value"):
                    set_profile(profile["key"], profile["value"])

            for knowledge in result.get("knowledge", []):
                if knowledge.get("title") and knowledge.get("content"):
                    add_knowledge(
                        category=knowledge.get("category", "general"),
                        title=knowledge["title"],
                        content=knowledge["content"],
                        keywords=knowledge.get("keywords", ""),
                        conversation_id=conversation_id,
                    )

    except Exception:
        pass  # 提取失败不影响主流程


def _parse_extraction(content: str) -> Optional[dict]:
    """解析 LLM 返回的 JSON"""
    # 尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 尝试提取 JSON 块
    match = re.search(r'\{[\s\S]*\}', content)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None
