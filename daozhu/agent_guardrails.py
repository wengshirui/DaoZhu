"""
岛主 DaoZhu — Agent Guardrail 控制器（#082 工程控制论升级）
参考 hermes-agent tool_guardrails.py 设计。
纯函数模块，只返回 Decision，不执行任何副作用。

职责：
- 检测同一工具同参数连续失败 → 阻断
- 检测幂等工具重复相同结果 → 警告
- 连续失败达上限 → 注入恢复提示
- 相关性门控：检查工具是否在 plan.tools_needed 中（#082）
- 进展趋势检测：progress_score 序列的升/平/降（#082）
- 递进式响应：warn → 重规划 → 加速消耗（#082）
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


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


@dataclass
class TrendDecision:
    """进展趋势检测的决策"""
    action: str = "ok"  # ok | warn | replan | accelerate
    stall_count: int = 0
    message: str = ""


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


# ─── 相关性门控（#082 AC10/AC11）──────────────────────────────

class RelevanceGate:
    """检查工具调用是否在计划内（对偶控制：不阻断但施加 warn 代价）"""

    def __init__(self):
        self._accepted_tools: set[str] = set()  # 探索成功后接纳的工具

    def reset(self):
        self._accepted_tools.clear()

    def check(self, tool_name: str, plan_tools: list[str]) -> GuardrailDecision:
        """
        检查工具是否在计划中。

        AC10: 不在 plan.tools_needed 中 → warn 但不阻断
        AC11: 计划外工具成功且 score 涨了 → 接纳，不再重复 warn
        """
        if not plan_tools:
            return GuardrailDecision(tool_name=tool_name)

        if tool_name in plan_tools:
            return GuardrailDecision(tool_name=tool_name)

        if tool_name in self._accepted_tools:
            return GuardrailDecision(tool_name=tool_name)

        return GuardrailDecision(
            action="warn",
            message=f"{tool_name} 不在执行计划中，请确认是否有必要调用。",
            tool_name=tool_name,
        )

    def accept_tool(self, tool_name: str):
        """探索成功 → 接纳该工具，后续不再 warn"""
        self._accepted_tools.add(tool_name)


# ─── 进展趋势检测（#082 AC7/AC8）─────────────────────────────

class ProgressTrend:
    """
    纯代码追踪 progress_score 序列，检测趋势。

    职责（设计决策 D5）：
    - solver 输出 score（位置）
    - 本模块看趋势（速度/方向）
    - 递进式响应（D8）：1轮不涨→warn，2轮→replan，3轮→accelerate
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self._scores: list[float] = []
        self._stall_count: int = 0

    @property
    def scores(self) -> list[float]:
        return self._scores.copy()

    @property
    def stall_count(self) -> int:
        return self._stall_count

    def record(self, score: float) -> TrendDecision:
        """
        记录新的 progress_score 并返回趋势决策。

        递进式响应（AC8）：
        - 1轮不涨 → warn
        - 2轮不涨 → replan
        - 3轮不涨 → accelerate
        """
        self._scores.append(score)

        # 至少需要 2 个数据点才能判趋势
        if len(self._scores) < 2:
            return TrendDecision(action="ok")

        prev = self._scores[-2]
        curr = self._scores[-1]

        # 判断是否有进展（允许微小浮动）
        improved = curr > prev + 0.01

        if improved:
            self._stall_count = 0
            return TrendDecision(action="ok")

        # 没有进展
        self._stall_count += 1

        if self._stall_count >= 3:
            return TrendDecision(
                action="accelerate",
                stall_count=self._stall_count,
                message=f"连续 {self._stall_count} 轮无进展，加速消耗 budget 准备中止。",
            )
        elif self._stall_count >= 2:
            return TrendDecision(
                action="replan",
                stall_count=self._stall_count,
                message=f"连续 {self._stall_count} 轮无进展，触发重规划。",
            )
        else:
            return TrendDecision(
                action="warn",
                stall_count=self._stall_count,
                message="本轮未取得进展，请换个方法或检查当前策略。",
            )
