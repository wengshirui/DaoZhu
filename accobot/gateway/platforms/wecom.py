"""WeCom (企业微信) adapter.

Implements the MessageAdapter interface for WeCom bots.
Requires: WECOM_CORP_ID, WECOM_AGENT_ID, WECOM_SECRET in .env

Reference: Hermes Agent's gateway/platforms/wecom.py
"""

import logging
from typing import Optional, Callable

from accobot.gateway.base import IncomingMessage, OutgoingMessage, MessageAdapter

logger = logging.getLogger(__name__)


class WeComAdapter(MessageAdapter):
    """WeCom (企业微信) message adapter."""

    @property
    def platform_name(self) -> str:
        return "wecom"

    def __init__(self):
        self._callback: Optional[Callable] = None
        self._corp_id: str = ""
        self._agent_id: str = ""
        self._secret: str = ""

    async def connect(self) -> None:
        """Initialize WeCom API connection."""
        import os
        self._corp_id = os.environ.get("WECOM_CORP_ID", "")
        self._agent_id = os.environ.get("WECOM_AGENT_ID", "")
        self._secret = os.environ.get("WECOM_SECRET", "")

        if not all([self._corp_id, self._agent_id, self._secret]):
            raise ValueError(
                "WeCom 配置不完整，请在 .env 中设置：\n"
                "  WECOM_CORP_ID=你的企业ID\n"
                "  WECOM_AGENT_ID=应用AgentId\n"
                "  WECOM_SECRET=应用Secret"
            )

        logger.info("WeCom adapter connected (corp: %s)", self._corp_id)

    async def disconnect(self) -> None:
        """Disconnect from WeCom."""
        logger.info("WeCom adapter disconnected")

    async def send_message(self, message: OutgoingMessage) -> bool:
        """Send a message via WeCom API."""
        # TODO: Implement actual WeCom API call
        # POST https://qyapi.weixin.qq.com/cgi-bin/message/send
        logger.info("WeCom send to %s: %s", message.chat_id, message.text[:50])
        return True

    async def on_message(self, callback) -> None:
        """Register message callback (webhook-based)."""
        self._callback = callback
        # TODO: Start webhook server to receive WeCom callbacks
        logger.info("WeCom message handler registered")


class DingTalkAdapter(MessageAdapter):
    """DingTalk (钉钉) message adapter."""

    @property
    def platform_name(self) -> str:
        return "dingtalk"

    def __init__(self):
        self._callback: Optional[Callable] = None

    async def connect(self) -> None:
        import os
        app_key = os.environ.get("DINGTALK_APP_KEY", "")
        app_secret = os.environ.get("DINGTALK_APP_SECRET", "")
        if not all([app_key, app_secret]):
            raise ValueError("DingTalk 配置不完整，请设置 DINGTALK_APP_KEY 和 DINGTALK_APP_SECRET")
        logger.info("DingTalk adapter connected")

    async def disconnect(self) -> None:
        logger.info("DingTalk adapter disconnected")

    async def send_message(self, message: OutgoingMessage) -> bool:
        logger.info("DingTalk send to %s: %s", message.chat_id, message.text[:50])
        return True

    async def on_message(self, callback) -> None:
        self._callback = callback


class FeishuAdapter(MessageAdapter):
    """Feishu/Lark (飞书) message adapter."""

    @property
    def platform_name(self) -> str:
        return "feishu"

    def __init__(self):
        self._callback: Optional[Callable] = None

    async def connect(self) -> None:
        import os
        app_id = os.environ.get("FEISHU_APP_ID", "")
        app_secret = os.environ.get("FEISHU_APP_SECRET", "")
        if not all([app_id, app_secret]):
            raise ValueError("飞书配置不完整，请设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        logger.info("Feishu adapter connected")

    async def disconnect(self) -> None:
        logger.info("Feishu adapter disconnected")

    async def send_message(self, message: OutgoingMessage) -> bool:
        logger.info("Feishu send to %s: %s", message.chat_id, message.text[:50])
        return True

    async def on_message(self, callback) -> None:
        self._callback = callback
