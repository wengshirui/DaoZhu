"""AccoBot Agent — core conversation loop.

Simplified from Hermes Agent's AIAgent class.
Handles: LLM calls, tool dispatch, message history, iteration control.
"""

import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

from openai import OpenAI

from accobot.config import get_api_key, load_config
from accobot.tools.registry import discover_tools, registry

logger = logging.getLogger(__name__)

# System prompt for the accounting assistant
DEFAULT_SYSTEM_PROMPT = """你是 AccoBot，一个智能财务助手。你帮助用户管理会计工作，包括：
- 原始凭证管理（录入、查询、OCR识别）
- 开票（根据你的描述去税务局开票）
- 做账（生成会计分录、审核、过账）
- 对账（银行流水匹配）
- 报税（税额计算、申报表生成）
- 账簿查看（总账、明细账、科目余额表）
- 报表（资产负债表、利润表、现金流量表）
- 数据分析（趋势、异常预警）

根据用户角色调整交互风格：
- 小企业负责人：用通俗易懂的语言，主动解释专业概念
- 专业会计：用专业术语，高效简洁
- 代账公司员工：强调效率，支持多账套操作

你有权调用工具来完成具体操作。每次调用工具后，根据结果向用户反馈。
如果用户的指令不够明确，主动询问缺失信息。
发现风险时主动提示（合规风险、数据异常等）。

## Skills（操作流程知识库）

如果下方列出的 Skill 与当前任务相关，你必须先调用 skill_view(name) 加载它的完整内容，然后按其中的步骤执行。
Skill 包含经过验证的操作流程、注意事项和最佳实践，优先于你的通用知识。

### 创建 Skill 的规则（重要）
当用户要求保存操作流程为 Skill 时：
1. 先调用 skill_view("create-skill") 加载创建规范
2. 必须基于**本次对话中实际执行过的操作步骤**来编写 Skill 内容，不要臆想或编造步骤
3. 如果对话中没有相关操作记录，先问用户具体步骤是什么
4. 用户修正了你的操作后，主动提议"要不要把这个流程保存为 Skill？"

{skills_index}
"""


class AccoAgent:
    """Core agent that manages the conversation loop and tool dispatch."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        on_token: Optional[Callable[[str], None]] = None,
    ):
        self.config = config or load_config()
        self.on_token = on_token  # streaming callback

        # Build system prompt with skill index + SOUL.md + standard rules
        base_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        skills_index = self._build_skills_index()
        soul_content = self._load_soul()
        standard_rules = self._load_standard_rules()
        self.system_prompt = base_prompt.replace("{skills_index}", skills_index) + soul_content + standard_rules

        # LLM client setup
        model_config = self.config.get("model", {})
        api_key = get_api_key(self.config)
        base_url = model_config.get("base_url")

        if not api_key:
            raise ValueError(
                "未配置 API Key。请在 ~/.accobot/.env 文件中设置：\n"
                "  DEEPSEEK_API_KEY=sk-xxx\n"
                "或设置环境变量 DEEPSEEK_API_KEY"
            )

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model_config.get("model_name", "gpt-4o")
        self.max_iterations = model_config.get("max_iterations", 90)

        # Conversation state
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt}
        ]

        # Discover and register tools
        discover_tools()

        # Discover MCP tools (if configured)
        self._discover_mcp()

    def _build_skills_index(self) -> str:
        """Build the skill index for system prompt injection."""
        try:
            from accobot.skills.loader import build_skills_index
            index = build_skills_index()
            return index if index else "(暂无可用 Skill)"
        except Exception as e:
            logger.debug("Failed to build skills index: %s", e)
            return "(Skill 系统未就绪)"

    def _load_soul(self) -> str:
        """Load SOUL.md for system prompt customization."""
        try:
            from accobot.soul import load_soul
            return load_soul()
        except Exception as e:
            logger.debug("Failed to load SOUL.md: %s", e)
            return ""

    def _load_standard_rules(self) -> str:
        """Load accounting standard rules for current company (REQ-023)."""
        try:
            from accobot.db.manager import DBManager
            from accobot.db.standards import load_standard_rules_summary
            mgr = DBManager.get_instance()
            company_dir = mgr.get_company_dir()
            if company_dir:
                return load_standard_rules_summary(company_dir)
        except Exception as e:
            logger.debug("Failed to load standard rules: %s", e)
        return ""

    def _maybe_compress(self) -> None:
        """Compress message history if it exceeds token threshold."""
        try:
            from accobot.session_compress import compress_messages
            self.messages = compress_messages(self.messages)
        except Exception as e:
            logger.debug("Session compression failed: %s", e)

    def _discover_mcp(self) -> None:
        """Discover and register MCP tools from configured servers."""
        try:
            from accobot.mcp.client import discover_mcp_tools
            tool_names = discover_mcp_tools()
            if tool_names:
                logger.info("MCP: registered %d tool(s)", len(tool_names))
        except ImportError:
            logger.debug("MCP SDK not available")
        except Exception as e:
            logger.debug("MCP discovery failed: %s", e)

    def _sanitize_messages(self) -> List[Dict[str, Any]]:
        """Sanitize messages before sending to LLM.

        Strips non-standard fields that strict providers (Moonshot, Kimi,
        通义千问) reject with HTTP 400. Only keeps fields defined in the
        OpenAI Chat Completions spec.
        """
        allowed_keys = {
            "system": {"role", "content", "name"},
            "user": {"role", "content", "name"},
            "assistant": {"role", "content", "tool_calls", "refusal"},
            "tool": {"role", "content", "tool_call_id"},
        }
        sanitized = []
        for msg in self.messages:
            role = msg.get("role", "user")
            keys = allowed_keys.get(role, {"role", "content"})
            clean = {k: v for k, v in msg.items() if k in keys}
            # Remove empty content for assistant messages with tool_calls
            if role == "assistant" and "tool_calls" in clean and not clean.get("content"):
                clean["content"] = ""
            sanitized.append(clean)
        return sanitized

    def chat(self, user_message: str) -> str:
        """Simple interface — send a message, get a response.

        Handles the full tool-calling loop internally.
        Returns the final text response.
        """
        self.messages.append({"role": "user", "content": user_message})

        # Compress session if too long
        self._maybe_compress()

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            # Get tool definitions
            tool_defs = registry.get_definitions()

            # Call LLM
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": self._sanitize_messages(),
            }
            if tool_defs:
                kwargs["tools"] = tool_defs
                kwargs["tool_choice"] = "auto"

            try:
                if self.on_token:
                    # Streaming mode
                    response = self._stream_response(**kwargs)
                else:
                    response = self.client.chat.completions.create(**kwargs)
                    response = response.choices[0].message
            except Exception as e:
                logger.error("LLM call failed: %s", e)
                error_msg = f"抱歉，调用模型时出错：{e}"
                self.messages.append({"role": "assistant", "content": error_msg})
                return error_msg

            # Check if there are tool calls
            if response.tool_calls:
                # Add assistant message with tool calls
                self.messages.append({
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in response.tool_calls
                    ],
                })

                # Execute each tool call
                for tool_call in response.tool_calls:
                    name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    logger.info("Calling tool: %s(%s)", name, args)
                    result = registry.dispatch(name, args)

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
            else:
                # No tool calls — final response
                content = response.content or ""
                self.messages.append({"role": "assistant", "content": content})
                return content

        # Max iterations reached — give one grace call without tools
        # so the agent can summarize what it accomplished and what's left
        logger.info("Max iterations (%d) reached, making grace call", self.max_iterations)
        try:
            grace_response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages + [{
                    "role": "system",
                    "content": "你已达到本次对话的工具调用上限。请总结你已完成的操作和剩余未完成的步骤，告诉用户接下来该怎么做。不要再调用工具。",
                }],
            )
            content = grace_response.choices[0].message.content or ""
            if content:
                self.messages.append({"role": "assistant", "content": content})
                return content
        except Exception:
            pass

        fallback = "操作步骤较多，已达到单次对话的处理上限。请继续告诉我接下来要做什么。"
        self.messages.append({"role": "assistant", "content": fallback})
        return fallback

    def _stream_response(self, **kwargs):
        """Stream response and collect the full message."""
        stream = self.client.chat.completions.create(stream=True, **kwargs)

        content_parts = []
        tool_calls_data: Dict[int, Dict] = {}

        for chunk in stream:
            delta = chunk.choices[0].delta

            # Stream text content
            if delta.content:
                content_parts.append(delta.content)
                if self.on_token:
                    self.on_token(delta.content)

            # Collect tool calls
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_data:
                        tool_calls_data[idx] = {
                            "id": tc_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }
                    if tc_delta.id:
                        tool_calls_data[idx]["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            tool_calls_data[idx]["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            tool_calls_data[idx]["arguments"] += tc_delta.function.arguments

        # Build a response object that matches non-streaming format
        class _FakeMessage:
            pass

        msg = _FakeMessage()
        msg.content = "".join(content_parts) if content_parts else None

        if tool_calls_data:
            class _FakeToolCall:
                pass

            class _FakeFunction:
                pass

            msg.tool_calls = []
            for idx in sorted(tool_calls_data.keys()):
                tc = _FakeToolCall()
                tc.id = tool_calls_data[idx]["id"]
                tc.function = _FakeFunction()
                tc.function.name = tool_calls_data[idx]["name"]
                tc.function.arguments = tool_calls_data[idx]["arguments"]
                msg.tool_calls.append(tc)
        else:
            msg.tool_calls = None

        return msg

    def reset(self) -> None:
        """Reset conversation history, keeping system prompt."""
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def get_history(self) -> List[Dict[str, Any]]:
        """Return conversation history (excluding system prompt)."""
        return [m for m in self.messages if m["role"] != "system"]
