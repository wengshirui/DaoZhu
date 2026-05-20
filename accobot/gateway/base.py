"""Base message adapter interface.

All platform adapters (WeChat, DingTalk, Feishu) implement this interface.
Inspired by Hermes Agent's gateway/platforms/base.py pattern.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class IncomingMessage:
    """A message received from a platform."""
    platform: str           # "wechat", "dingtalk", "feishu"
    user_id: str            # Platform-specific user identifier
    chat_id: str            # Conversation/group identifier
    text: str               # Message text content
    message_id: str = ""    # Platform message ID
    image_url: str = ""     # Attached image URL (if any)
    file_url: str = ""      # Attached file URL (if any)
    file_name: str = ""     # Attached file name


@dataclass
class OutgoingMessage:
    """A message to send to a platform."""
    chat_id: str
    text: str
    image_path: str = ""    # Local image file to send
    file_path: str = ""     # Local file to send


class MessageAdapter(ABC):
    """Base class for all platform adapters."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier (e.g., 'wechat')."""
        ...

    @abstractmethod
    async def connect(self) -> None:
        """Initialize connection to the platform."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the platform."""
        ...

    @abstractmethod
    async def send_message(self, message: OutgoingMessage) -> bool:
        """Send a message to the platform. Returns True on success."""
        ...

    @abstractmethod
    async def on_message(self, callback) -> None:
        """Register a callback for incoming messages.

        callback signature: async def handler(msg: IncomingMessage) -> Optional[str]
        If callback returns a string, it's sent as a reply.
        """
        ...

    async def send_text(self, chat_id: str, text: str) -> bool:
        """Convenience: send a text message."""
        return await self.send_message(OutgoingMessage(chat_id=chat_id, text=text))
