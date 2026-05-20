"""Gateway runner — manages platform adapters and routes messages to Agent.

Inspired by Hermes Agent's gateway/run.py.
Starts adapters, receives messages, passes to Agent, sends replies.
"""

import asyncio
import logging
from typing import Dict, Optional

from accobot.agent import AccoAgent
from accobot.config import load_config, load_env
from accobot.gateway.base import IncomingMessage, MessageAdapter

logger = logging.getLogger(__name__)


class GatewayRunner:
    """Manages messaging platform adapters and routes messages to the Agent."""

    def __init__(self):
        self.adapters: Dict[str, MessageAdapter] = {}
        self.agent: Optional[AccoAgent] = None
        self._running = False

    def register_adapter(self, adapter: MessageAdapter) -> None:
        """Register a platform adapter."""
        self.adapters[adapter.platform_name] = adapter
        logger.info("Registered adapter: %s", adapter.platform_name)

    async def start(self) -> None:
        """Start all registered adapters and begin processing messages."""
        load_env()
        config = load_config()
        self.agent = AccoAgent(config=config)
        self._running = True

        # Connect all adapters
        for name, adapter in self.adapters.items():
            try:
                await adapter.connect()
                await adapter.on_message(self._handle_message)
                logger.info("Adapter %s connected", name)
            except Exception as e:
                logger.error("Failed to connect adapter %s: %s", name, e)

        logger.info("Gateway running with %d adapter(s)", len(self.adapters))

        # Keep running
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop all adapters."""
        self._running = False
        for name, adapter in self.adapters.items():
            try:
                await adapter.disconnect()
            except Exception as e:
                logger.error("Error disconnecting %s: %s", name, e)

    async def _handle_message(self, msg: IncomingMessage) -> Optional[str]:
        """Process an incoming message through the Agent."""
        if not self.agent:
            return "系统未就绪，请稍后再试"

        if not msg.text.strip():
            return None

        try:
            # Run agent synchronously in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.agent.chat, msg.text)
            return response
        except Exception as e:
            logger.exception("Agent error for message from %s: %s", msg.platform, e)
            return f"处理消息时出错：{e}"
