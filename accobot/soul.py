"""SOUL.md — User-customizable Agent identity and behavior rules.

Reads ~/.accobot/SOUL.md and injects its content into the system prompt.
If the file doesn't exist, creates a default template on first access.

Inspired by OpenClaw's SOUL.md pattern.
"""

import logging
from pathlib import Path
from accobot.config import get_accobot_home

logger = logging.getLogger(__name__)

DEFAULT_SOUL = """# AccoBot 身份配置

## 角色
你是一个专业的财务助手，服务于中国中小企业。

## 风格
- 对不懂会计的用户：用通俗易懂的语言，主动解释专业概念
- 对专业会计：用专业术语，高效简洁
- 始终保持耐心和友好

## 行为规则
- 涉及金额操作时，先确认再执行
- 发现风险时主动提示（合规风险、数据异常）
- 不确定的事情如实说"我不确定"，不编造答案
- 操作完成后简要汇报结果

## 专业偏好
- 默认使用小企业会计准则
- 金额保留两位小数
- 日期格式：YYYY-MM-DD

## 自定义区域
<!-- 在下方添加你的自定义规则，Agent 会遵守 -->

"""


def get_soul_path() -> Path:
    """Return the path to SOUL.md."""
    return get_accobot_home() / "SOUL.md"


def load_soul() -> str:
    """Load SOUL.md content. Creates default template if not exists.

    Returns the content string to be appended to the system prompt.
    """
    soul_path = get_soul_path()

    if not soul_path.exists():
        # Create default template
        try:
            soul_path.parent.mkdir(parents=True, exist_ok=True)
            soul_path.write_text(DEFAULT_SOUL, encoding="utf-8")
            logger.info("Created default SOUL.md at %s", soul_path)
        except Exception as e:
            logger.warning("Failed to create SOUL.md: %s", e)
            return ""

    try:
        content = soul_path.read_text(encoding="utf-8").strip()
        if content:
            return f"\n\n## 用户自定义规则（来自 SOUL.md）\n\n{content}"
        return ""
    except Exception as e:
        logger.warning("Failed to read SOUL.md: %s", e)
        return ""
