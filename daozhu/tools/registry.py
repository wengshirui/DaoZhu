"""
岛主 DaoZhu — 工具注册表
参考: Hermes-Agent tools/registry.py（简化版）
职责: 注册工具 schema + handler，供 Agent Loop 调用
"""

import json
import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class ToolEntry:
    """工具注册条目"""
    name: str
    description: str
    parameters: dict  # OpenAI function calling 格式的 parameters
    handler: Callable  # async def handler(**kwargs) -> str
    category: str = "general"
    emoji: str = "⚡"


class ToolRegistry:
    """工具注册表（全局单例）"""

    def __init__(self):
        self._tools: dict[str, ToolEntry] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable,
        category: str = "general",
        emoji: str = "⚡",
    ):
        """注册一个工具"""
        self._tools[name] = ToolEntry(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            category=category,
            emoji=emoji,
        )

    def get_schemas(self) -> list[dict]:
        """获取所有工具的 OpenAI function calling schema"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    async def dispatch(self, name: str, arguments: dict) -> str:
        """调度工具调用，返回 JSON 字符串结果"""
        tool = self._tools.get(name)
        if not tool:
            return json.dumps({"error": f"工具不存在: {name}"})

        # 防御性检查：确保 arguments 是 dict
        if not isinstance(arguments, dict):
            arguments = {}

        # 检查必填参数
        required = tool.parameters.get("required", [])
        missing = [p for p in required if p not in arguments]
        if missing:
            return json.dumps({
                "error": f"缺少必填参数: {missing}。请提供完整参数后重试。",
                "required": required,
                "received": list(arguments.keys()),
            }, ensure_ascii=False)

        start = time.monotonic()
        try:
            result = await tool.handler(**arguments)
            duration_ms = int((time.monotonic() - start) * 1000)

            # 记录 skill 使用
            from ..memory_db import track_skill_usage
            track_skill_usage(name, "call", success=True, duration_ms=duration_ms)

            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            from ..memory_db import track_skill_usage
            track_skill_usage(name, "call", success=False, duration_ms=duration_ms)

            error_msg = f"工具执行失败 [{name}]: {str(e)}"
            if "missing" in str(e) and "positional argument" in str(e):
                error_msg += f" (收到的参数: {list(arguments.keys())})"
            logger.error(error_msg)
            return json.dumps({"error": error_msg}, ensure_ascii=False)

    def list_tools(self) -> list[dict]:
        """列出所有已注册工具"""
        return [
            {"name": t.name, "description": t.description,
             "category": t.category, "emoji": t.emoji}
            for t in self._tools.values()
        ]

    def has_tool(self, name: str) -> bool:
        return name in self._tools


# 全局单例
registry = ToolRegistry()
