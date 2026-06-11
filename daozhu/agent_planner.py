"""
岛主 DaoZhu — 执行规划器（#082 工程控制论升级）
基于意图和可用工具，生成结构化执行计划。
支持在线重规划（自适应控制）。

计划不是给用户看的——是注入到 LLM 上下文中，引导它有目的地调工具。
"""

import json
import logging

from .chat_service import call_llm_simple
from .tools.registry import registry

logger = logging.getLogger(__name__)

PLAN_PROMPT = """你是执行规划器。基于用户意图和可用工具，输出一个执行计划。只输出 JSON。

用户意图：{goal}
解决标准：{solved_when}

可用工具：{tool_names}

输出格式（严格 JSON）：
{{"goal": "要达成什么", "steps": ["步骤1", "步骤2"], "fallback": "如果主路径失败的替代方案", "tools_needed": ["工具名1"]}}

规则：
- steps 最多 3 步，每步简洁一句话
- 没有直接对应的工具？→ 考虑用 web_search 搜索、或组合多个工具间接完成
- fallback 必须是具体的替代路径（不要写"诚实告知"除非真的无解）
- 不要过度规划——简单任务 1 步就够"""


async def make_plan(intent: dict) -> dict:
    """
    基于意图生成执行计划。返回结构化 plan 字典。
    失败时返回简单直通计划（不阻塞执行）。
    """
    goal = intent.get("goal", "")
    solved_when = intent.get("solved_when", "")

    # 获取工具名列表
    tool_names = [s["function"]["name"] for s in registry.get_schemas()]
    tool_names_str = ", ".join(tool_names) if tool_names else "无"

    prompt = PLAN_PROMPT.format(
        goal=goal[:150],
        solved_when=solved_when[:100],
        tool_names=tool_names_str[:300],
    )

    raw = await call_llm_simple(prompt, max_tokens=200)

    if not raw:
        logger.warning("[Planner] LLM 调用失败，使用直通计划")
        return _passthrough_plan(goal)

    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        plan = json.loads(text)

        # 校验
        plan.setdefault("goal", goal)
        plan.setdefault("steps", ["直接执行"])
        plan.setdefault("fallback", "诚实告知用户")
        plan.setdefault("tools_needed", [])

        # 确保 steps 是列表
        if not isinstance(plan["steps"], list):
            plan["steps"] = [str(plan["steps"])]

        logger.info(
            f"[Planner] 计划生成: {len(plan['steps'])} 步, "
            f"tools={plan['tools_needed'][:3]}"
        )
        return plan

    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"[Planner] JSON 解析失败: {e}")
        return _passthrough_plan(goal)


def _passthrough_plan(goal: str) -> dict:
    """兜底计划：不阻塞，让执行循环正常跑"""
    return {
        "goal": goal,
        "steps": ["根据用户请求直接执行"],
        "fallback": "诚实告知用户",
        "tools_needed": [],
    }


def format_plan_for_context(plan: dict) -> str:
    """将计划格式化为可注入 LLM 上下文的文本"""
    steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(plan["steps"]))
    return (
        f"[执行计划]\n"
        f"目标: {plan['goal']}\n"
        f"步骤:\n{steps_text}\n"
        f"备选: {plan['fallback']}"
    )


# ─── 在线重规划（#082 AC9）───────────────────────────────────

REPLAN_PROMPT = """你是执行规划器。基于已有执行记录，重新生成计划。只输出 JSON。

原始目标：{goal}
已完成步骤：{completed}
失败的工具：{failed_tools}
失败原因：{errors}

可用工具：{tool_names}

要求：
- 生成新的 steps 列表，跳过已完成的部分
- 避免使用已失败的工具（除非换参数）
- 给出新的 fallback 方案
- steps 最多 3 步

输出格式（严格 JSON）：
{{"goal": "...", "steps": ["新步骤1", "新步骤2"], "fallback": "...", "tools_needed": ["工具名"]}}"""


async def replan(
    original_plan: dict,
    completed_steps: list[str],
    failed_tools: list[str],
    errors: list[str],
) -> dict:
    """
    在线重规划：基于已有执行记录生成新 plan（AC9）。
    失败时保留原 plan（AC15）。

    Args:
        original_plan: 原始计划
        completed_steps: 已完成的步骤
        failed_tools: 失败的工具名列表
        errors: 错误原因列表

    Returns:
        新的 plan 字典（失败时返回原 plan）
    """
    goal = original_plan.get("goal", "")

    # 获取工具名列表
    tool_names = [s["function"]["name"] for s in registry.get_schemas()]
    tool_names_str = ", ".join(tool_names) if tool_names else "无"

    prompt = REPLAN_PROMPT.format(
        goal=goal[:150],
        completed=", ".join(completed_steps[:5]) if completed_steps else "无",
        failed_tools=", ".join(failed_tools[:3]) if failed_tools else "无",
        errors="; ".join(errors[:2]) if errors else "无",
        tool_names=tool_names_str[:300],
    )

    try:
        raw = await call_llm_simple(prompt, max_tokens=200)
        if not raw:
            logger.warning("[Replan] LLM 调用失败，保留原 plan")
            return original_plan

        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        new_plan = json.loads(text)

        new_plan.setdefault("goal", goal)
        new_plan.setdefault("steps", ["直接执行"])
        new_plan.setdefault("fallback", "诚实告知用户")
        new_plan.setdefault("tools_needed", [])

        if not isinstance(new_plan["steps"], list):
            new_plan["steps"] = [str(new_plan["steps"])]

        logger.info(
            f"[Replan] 重规划成功: {len(new_plan['steps'])} 步, "
            f"tools={new_plan['tools_needed'][:3]}"
        )
        return new_plan

    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"[Replan] 解析失败: {e}, 保留原 plan")
        return original_plan
    except Exception as e:
        logger.warning(f"[Replan] 异常: {e}, 保留原 plan")
        return original_plan
