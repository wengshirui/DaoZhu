"""
岛主 DaoZhu — Agent Guardrail 控制器（#079 Phase 3）
参考 hermes-agent tool_guardrails.py 设计。
纯函数模块，只返回 Decision，不执行任何副作用。

职责：
- 检测同一工具同参数连续失败 → 阻断
- 检测幂等工具重复相同结果 → 警告
- 连续失败达上限 → 注入恢复提示
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GuardrailDecision:
    """Guardrail 返回的决策"""
    action: str = "allow"  # allow | warn | block
    message: str = ""
    tool_name: str = ""
    count: int = 0

    @property
    def should_block(self) -> bool:
        return self.action == "block"


class ToolGuardrailController:
    """每轮对话的工具循环守卫（纯状态追踪，无副作用）"""

    # 阈值
    EXACT_FAILURE_WARN = 2
    EXACT_FAILURE_BLOCK = 4
    SAME_TOOL_FAILURE_WARN = 3
    NO_PROGRESS_WARN = 2

    def __init__(self):
        self.reset()

    def reset(self):
        """每轮对话开始时重置"""
        self._exact_failures: dict[str, int] = {}  # hash(name+args) → count
        self._same_tool_failures: dict[str, int] = {}  # tool_name → count
        self._last_results: dict[str, str] = {}  # hash(name+args) → result_hash
        self._no_progress: dict[str, int] = {}  # hash(name+args) → same_result_count

    def before_call(self, tool_name: str, args: dict) -> GuardrailDecision:
        """工具调用前检查：是否应该阻断"""
        sig = self._signature(tool_name, args)

        # 检查：同一调用连续失败过多
        fail_count = self._exact_failures.get(sig, 0)
        if fail_count >= self.EXACT_FAILURE_BLOCK:
            return GuardrailDecision(
                action="block",
                message=f"{tool_name} 同样的调用已失败 {fail_count} 次，停止重试。换个方式或告诉用户问题所在。",
                tool_name=tool_name,
                count=fail_count,
            )

        return GuardrailDecision(tool_name=tool_name)

    def after_call(self, tool_name: str, args: dict, result: str, failed: bool) -> GuardrailDecision:
        """工具调用后记录结果，返回建议"""
        sig = self._signature(tool_name, args)

        if failed:
            # 记录失败
            self._exact_failures[sig] = self._exact_failures.get(sig, 0) + 1
            self._same_tool_failures[tool_name] = self._same_tool_failures.get(tool_name, 0) + 1
            count = self._exact_failures[sig]

            if count >= self.EXACT_FAILURE_WARN:
                return GuardrailDecision(
                    action="warn",
                    message=f"{tool_name} 已失败 {count} 次（相同参数）。检查错误并换个策略，不要原样重试。",
                    tool_name=tool_name,
                    count=count,
                )

            same_count = self._same_tool_failures[tool_name]
            if same_count >= self.SAME_TOOL_FAILURE_WARN:
                return GuardrailDecision(
                    action="warn",
                    message=f"{tool_name} 本轮已失败 {same_count} 次。诊断问题后再决定下一步。",
                    tool_name=tool_name,
                    count=same_count,
                )
        else:
            # 成功：重置该签名的失败计数
            self._exact_failures.pop(sig, None)
            self._same_tool_failures.pop(tool_name, None)

            # 幂等检测：相同调用返回相同结果
            result_hash = hashlib.md5(result.encode()[:500]).hexdigest()[:16]
            if sig in self._last_results and self._last_results[sig] == result_hash:
                self._no_progress[sig] = self._no_progress.get(sig, 0) + 1
                if self._no_progress[sig] >= self.NO_PROGRESS_WARN:
                    return GuardrailDecision(
                        action="warn",
                        message=f"{tool_name} 返回了相同结果 {self._no_progress[sig]} 次。直接使用已有结果，不要重复调用。",
                        tool_name=tool_name,
                        count=self._no_progress[sig],
                    )
            else:
                self._no_progress.pop(sig, None)
            self._last_results[sig] = result_hash

        return GuardrailDecision(tool_name=tool_name)

    def _signature(self, tool_name: str, args: dict) -> str:
        """生成调用签名（tool_name + 参数的稳定 hash）"""
        canonical = json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
        return f"{tool_name}:{hashlib.md5(canonical.encode()).hexdigest()[:12]}"
