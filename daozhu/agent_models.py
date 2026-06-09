"""
岛主 DaoZhu — Agent 数据模型（#079）
定义 Pipeline 各阶段间传递的结构化数据。
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ToolCall:
    """单次工具调用记录"""
    tool_name: str
    args: dict = field(default_factory=dict)
    result: str = ""
    success: bool = True
    error: str = ""
    duration_ms: int = 0


@dataclass
class ExecutionRecord:
    """一轮对话中所有工具执行的结构化记录"""
    tool_calls: list[ToolCall] = field(default_factory=list)
    had_tool_calls: bool = False

    @property
    def errors(self) -> list[str]:
        return [tc.error for tc in self.tool_calls if not tc.success and tc.error]

    @property
    def success_count(self) -> int:
        return sum(1 for tc in self.tool_calls if tc.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for tc in self.tool_calls if not tc.success)

    def summary_text(self) -> str:
        """生成结构化摘要（供 responder 使用，包含实际返回数据）"""
        if not self.tool_calls:
            return "本轮未执行任何工具调用。"

        lines = []
        for tc in self.tool_calls:
            if tc.success:
                # 截取结果前 500 字符给 responder 参考
                result_preview = tc.result[:500] if tc.result else "（无返回数据）"
                lines.append(f"✅ {tc.tool_name} — 成功")
                lines.append(f"   返回数据: {result_preview}")
            else:
                lines.append(f"❌ {tc.tool_name} — 失败: {tc.error}")
        return "\n".join(lines)

    def numbers_in_results(self) -> set[int]:
        """提取所有工具返回中的数字（供验证器比对）"""
        import re
        numbers = set()
        for tc in self.tool_calls:
            if tc.success and tc.result:
                # 提取所有整数
                for match in re.finditer(r'\b(\d+)\b', tc.result):
                    n = int(match.group(1))
                    if 2 <= n <= 100000:  # 过滤掉 0/1 和超大数
                        numbers.add(n)
        return numbers
