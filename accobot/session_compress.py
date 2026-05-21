"""Session compression — prevent long conversations from exceeding token limits.

When message history grows too large, automatically compresses older messages
into a summary while preserving recent context.

Strategy:
1. Estimate token count of all messages
2. If over threshold, keep last N messages verbatim
3. Summarize older messages into a compact system note
4. Extract key facts to memory (if available)

Inspired by OpenClaw's session compaction and Hermes Agent's context compression.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Configuration
TOKEN_THRESHOLD = 8000       # Trigger compression above this estimate
KEEP_RECENT = 10             # Keep last N messages verbatim
CHARS_PER_TOKEN = 3          # Rough estimate for Chinese text (conservative)


def estimate_tokens(messages: List[Dict[str, Any]]) -> int:
    """Estimate token count for a list of messages."""
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        # Tool calls add overhead
        if msg.get("tool_calls"):
            total_chars += 200 * len(msg["tool_calls"])
    return total_chars // CHARS_PER_TOKEN


def compress_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compress message history if it exceeds the token threshold.

    Returns the (possibly compressed) message list.
    The first message (system prompt) is always preserved.
    """
    if not messages:
        return messages

    # Don't compress if under threshold
    token_estimate = estimate_tokens(messages)
    if token_estimate <= TOKEN_THRESHOLD:
        return messages

    logger.info(
        "Session compression triggered: ~%d tokens (threshold: %d)",
        token_estimate, TOKEN_THRESHOLD,
    )

    # Separate system prompt from conversation
    system_msgs = [m for m in messages if m.get("role") == "system"]
    conv_msgs = [m for m in messages if m.get("role") != "system"]

    if len(conv_msgs) <= KEEP_RECENT:
        return messages  # Not enough to compress

    # Split: old messages to summarize, recent to keep
    old_msgs = conv_msgs[:-KEEP_RECENT]
    recent_msgs = conv_msgs[-KEEP_RECENT:]

    # Build summary of old messages
    summary = _summarize_messages(old_msgs)

    # Construct compressed history
    compressed = system_msgs + [
        {
            "role": "system",
            "content": f"[对话历史摘要 — 以下是之前对话的关键信息]\n{summary}\n[摘要结束 — 以下是最近的对话]",
        }
    ] + recent_msgs

    new_tokens = estimate_tokens(compressed)
    logger.info(
        "Compressed: %d messages → %d messages (~%d → ~%d tokens)",
        len(messages), len(compressed), token_estimate, new_tokens,
    )

    return compressed


def _summarize_messages(messages: List[Dict[str, Any]]) -> str:
    """Create a compact summary of old messages.

    Uses heuristic extraction (no LLM call) to keep it fast and free.
    """
    facts = []
    actions = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if not content or not isinstance(content, str):
            continue

        if role == "user":
            # Extract user intents
            if len(content) > 5:
                facts.append(f"用户: {content[:80]}")
        elif role == "assistant":
            # Extract key results (look for ✅ or structured info)
            if "✅" in content:
                for line in content.split("\n"):
                    if "✅" in line:
                        actions.append(line.strip()[:100])
                        break
            elif len(content) > 10:
                # First meaningful line
                first_line = content.split("\n")[0][:80]
                if first_line:
                    actions.append(f"回复: {first_line}")
        elif role == "tool":
            # Extract tool results
            if "error" not in content.lower() and len(content) < 200:
                pass  # Skip verbose tool results

    # Build compact summary
    lines = []
    if facts:
        lines.append("用户提到的关键信息：")
        for f in facts[-5:]:  # Keep last 5 user messages
            lines.append(f"  - {f}")
    if actions:
        lines.append("已完成的操作：")
        for a in actions[-5:]:  # Keep last 5 actions
            lines.append(f"  - {a}")

    return "\n".join(lines) if lines else "（之前的对话内容已压缩）"
