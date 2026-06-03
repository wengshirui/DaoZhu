"""
岛主 DaoZhu — 会话自动压缩
参考: DeepSeek-Reasonix internal/agent/compact.go
职责: 当对话 prompt 接近 context window 上限时，自动压缩旧历史为结构化摘要
"""

import json
import logging
from typing import Optional

import httpx

from .config import get_config_value, get_api_key, get_provider_base_url, get_provider_model, get_provider_protocol

logger = logging.getLogger(__name__)

# 压缩参数（对齐 Reasonix）
COMPACT_RATIO = 0.75          # prompt 达到 window 的 75% 时触发
RECENT_KEEP = 8               # 保留最近 8 条消息不压缩
MIN_COMPACTABLE = 4           # 至少有 4 条可压缩消息才触发
TOKEN_PER_CHAR = 0.5          # 中文 token 估算：约 2 字符/token

# DeepSeek context window（根据模型不同可能需要调整）
DEFAULT_CONTEXT_WINDOW = 64000

# 压缩用的 prompt（直接从 Reasonix 翻译）
COMPACTION_PROMPT = """你正在压缩一个 AI 助手的早期对话历史。助手只保留你的摘要（原始消息会被删除），
所以它必须能仅凭摘要继续当前任务。

按以下标题输出，没有内容的标题跳过：

## 目标
用户的请求和意图，尽量保留原话。包含明确的需求、限制和偏好。

## 已做决定
到目前为止做出的关键选择和原因 — 避免后续重新讨论或推翻。

## 文件与代码
读过或修改过的文件，具体的关键信息：签名、行号、数据结构、已做的编辑。要具体。

## 执行过的命令
运行过的命令和相关结果 — 什么通过了、什么失败了、关键错误信息。

## 错误与修复
遇到的问题和如何解决的（或未解决的），避免重复踩坑。

## 待完成与下一步
仍在进行或未开始的工作，以及最具体的下一步操作。

规则：简洁 — 用列表和片段，不用散文。精确保留标识符、路径和数字。不要编造消息中没有的内容。"""


def estimate_tokens(messages: list[dict]) -> int:
    """估算消息列表的 token 数（粗略但快速）"""
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            # Anthropic 格式
            for block in content:
                if isinstance(block, dict):
                    total_chars += len(str(block.get("content", "")))
                    total_chars += len(str(block.get("text", "")))
    return int(total_chars * TOKEN_PER_CHAR)


def should_compact(messages: list[dict], context_window: int = DEFAULT_CONTEXT_WINDOW) -> bool:
    """判断是否需要压缩"""
    tokens = estimate_tokens(messages)
    threshold = int(context_window * COMPACT_RATIO)
    return tokens > threshold and _count_compactable(messages) >= MIN_COMPACTABLE


def _count_compactable(messages: list[dict]) -> int:
    """计算可压缩的消息数（排除 system 和最近 RECENT_KEEP 条）"""
    non_system = [m for m in messages if m.get("role") != "system"]
    return max(0, len(non_system) - RECENT_KEEP)


async def compact_messages(messages: list[dict], conversation_id: str = "") -> list[dict]:
    """
    压缩消息列表：保留 system + 摘要 + 最近 RECENT_KEEP 条
    如果提供 conversation_id，将被压缩的旧消息在 DB 中标记为 active=0（归档）
    返回压缩后的新消息列表
    """
    # 分离 system 消息和对话消息
    system_msgs = [m for m in messages if m.get("role") == "system"]
    conversation = [m for m in messages if m.get("role") != "system"]

    if len(conversation) <= RECENT_KEEP:
        return messages  # 不需要压缩

    # 分割：要压缩的旧消息 + 保留的最近消息
    to_compress = conversation[:-RECENT_KEEP]
    recent_tail = conversation[-RECENT_KEEP:]

    # 调用 LLM 生成摘要
    summary = await _generate_summary(to_compress)
    if not summary:
        return messages  # 压缩失败，保持原样

    # === AC6: 归档被压缩的消息到 DB（标记 active=0）===
    if conversation_id:
        try:
            _archive_compressed_messages(conversation_id, len(to_compress))
        except Exception as e:
            logger.warning(f"归档压缩消息失败: {e}")

    # 构建压缩后的消息列表
    summary_msg = {
        "role": "assistant",
        "content": f"[以下是早期对话的压缩摘要，原始消息已归档：]\n\n{summary}",
    }

    result = system_msgs + [summary_msg] + recent_tail
    logger.info(
        f"会话压缩完成: {len(messages)} → {len(result)} 条消息, "
        f"压缩了 {len(to_compress)} 条旧消息"
    )
    return result


def _archive_compressed_messages(conversation_id: str, count: int):
    """将最早的 N 条消息标记为 active=0（归档，不删除）"""
    import sqlite3
    from .config import PLATFORM_ROOT

    db_path = PLATFORM_ROOT / "chat.db"
    conn = sqlite3.connect(str(db_path))
    # 找到该对话最早的 count 条活跃非 system 消息，标记为 active=0
    conn.execute(
        """UPDATE messages SET active = 0
           WHERE id IN (
               SELECT id FROM messages
               WHERE conversation_id = ? AND active = 1 AND role != 'system'
               ORDER BY id ASC LIMIT ?
           )""",
        (conversation_id, count),
    )
    conn.commit()
    conn.close()
    logger.info(f"已归档 {count} 条消息 (conv={conversation_id})")


async def _generate_summary(messages_to_compress: list[dict]) -> Optional[str]:
    """调用 LLM 生成压缩摘要"""
    provider = get_config_value("ai.provider", "deepseek")
    model = get_provider_model(provider)
    api_key = get_api_key(provider)
    base_url = get_provider_base_url(provider)
    protocol = get_provider_protocol(provider)

    if not api_key:
        return None

    # 构建压缩请求
    compress_content = ""
    for msg in messages_to_compress:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, list):
            # Anthropic tool_result 格式
            content = str(content)
        # 截断过长的工具结果
        if role == "tool" and len(content) > 500:
            content = content[:500] + "...(truncated)"
        compress_content += f"[{role}]: {content}\n\n"

    request_messages = [
        {"role": "system", "content": COMPACTION_PROMPT},
        {"role": "user", "content": compress_content},
    ]

    try:
        if protocol == "anthropic":
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            payload = {"model": model, "messages": [{"role": "user", "content": compress_content}],
                       "system": COMPACTION_PROMPT, "max_tokens": 1500}
            endpoint = f"{base_url}/v1/messages"
        else:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": model, "messages": request_messages, "max_tokens": 1500}
            endpoint = f"{base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.warning(f"压缩调用失败: HTTP {resp.status_code}")
                return None

            data = resp.json()
            if protocol == "anthropic":
                blocks = data.get("content", [])
                return "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text")
            else:
                return data["choices"][0]["message"].get("content", "")

    except Exception as e:
        logger.warning(f"压缩调用异常: {e}")
        return None
