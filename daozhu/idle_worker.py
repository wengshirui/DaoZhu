"""
岛主 DaoZhu — AI 空闲自主工作引擎（#073 Phase 3）
职责：检测用户空闲 → AI 自主决策执行任务 → 生成工作汇报
思想基石：用户是谁 → 他想干什么 → 怎么帮他更好地实现

优化原则（v2）：
1. 不只看时间长短，看"有没有值得汇报的事"
2. 冷却基于"有没有新内容"，而非固定时间
3. 任务类型可扩展（注册机制）
4. 支持窗口 refocus 重新触发
5. 复盘结合用户事项分类框架
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Callable, Awaitable

from .config import PLATFORM_ROOT, get_config_value

logger = logging.getLogger(__name__)

IDLE_DB_PATH = PLATFORM_ROOT / "idle_work.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    detail TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS idle_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary TEXT NOT NULL,
    tasks_executed TEXT DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    shown INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_log(created_at);
"""


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(IDLE_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


# === 交互时间追踪 ===

_last_interaction: Optional[datetime] = None
_last_report_hash: str = ""  # 上次汇报内容的 hash，避免重复内容


def record_interaction(event_type: str = "api_call", detail: str = ""):
    """记录一次用户交互"""
    global _last_interaction
    _last_interaction = datetime.now()


def get_last_interaction() -> datetime:
    """获取最后交互时间"""
    global _last_interaction
    if _last_interaction:
        return _last_interaction
    try:
        db = _get_db()
        row = db.execute(
            "SELECT created_at FROM activity_log ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        db.close()
        if row:
            _last_interaction = datetime.fromisoformat(row["created_at"])
            return _last_interaction
    except Exception:
        pass
    _last_interaction = datetime.now()
    return _last_interaction


def get_idle_minutes() -> float:
    """获取当前空闲分钟数"""
    last = get_last_interaction()
    return (datetime.now() - last).total_seconds() / 60


# === 可扩展任务注册机制（优化点3）===

_registered_tasks: list[dict] = []


def register_idle_task(name: str, handler: Callable, priority: int = 50,
                       min_idle_minutes: int = 0):
    """
    注册一个空闲自主任务。
    handler: async def fn() -> Optional[str]，返回结果文本或 None
    priority: 越小越先执行
    min_idle_minutes: 至少空闲多久才触发此任务（0=总是检查）
    """
    _registered_tasks.append({
        "name": name,
        "handler": handler,
        "priority": priority,
        "min_idle_minutes": min_idle_minutes,
    })
    _registered_tasks.sort(key=lambda t: t["priority"])


# === 智能触发逻辑（优化点1+2）===

_last_idle_run: Optional[datetime] = None


async def check_and_run():
    """
    定时调用（每分钟）：智能决策是否执行自主任务。
    不只看空闲时间，还看"有没有值得做的事"。
    """
    global _last_idle_run, _last_report_hash

    # 检查开关
    enabled = get_config_value("greeting.enabled", True)
    if not enabled:
        return

    idle_mins = get_idle_minutes()
    threshold_mins = get_config_value("greeting.idle_threshold_hours", 2) * 60

    # 基础门槛：至少空闲 30 分钟才开始检查（避免用户只是去倒杯水）
    if idle_mins < 30:
        return

    # 收集所有应该执行的任务
    tasks_to_run = []
    for task in _registered_tasks:
        if idle_mins >= task["min_idle_minutes"]:
            tasks_to_run.append(task)

    if not tasks_to_run:
        return

    # 智能冷却（优化点2）：检查是否有新内容值得汇报
    # 如果上次汇报不到 1 小时前，只执行"紧急"任务（待办到期）
    if _last_idle_run:
        since_last_mins = (datetime.now() - _last_idle_run).total_seconds() / 60
        if since_last_mins < 60:
            # 1小时内只跑优先级最高的任务（待办检查）
            tasks_to_run = [t for t in tasks_to_run if t["priority"] <= 10]
            if not tasks_to_run:
                return
        elif since_last_mins < threshold_mins:
            # 阈值内不重跑非紧急任务
            if idle_mins < threshold_mins:
                return

    # 执行任务
    logger.info(f"用户空闲 {idle_mins:.0f} 分钟，执行 {len(tasks_to_run)} 项自主任务...")
    results = []

    for task in tasks_to_run:
        try:
            result = await task["handler"]()
            if result:
                results.append({"type": task["name"], "result": result})
        except Exception as e:
            logger.warning(f"自主任务 {task['name']} 失败: {e}")

    if not results:
        return

    # 去重：如果内容跟上次一样，不重复存储
    content_hash = hash(json.dumps(results, ensure_ascii=False))
    if str(content_hash) == _last_report_hash:
        return

    _last_report_hash = str(content_hash)
    _last_idle_run = datetime.now()
    _save_report(results)
    logger.info(f"自主工作完成: {len(results)} 项有新内容")


# === 内置任务实现 ===

async def _task_check_todos() -> Optional[str]:
    """待办到期检查（优先级最高：紧急信息）"""
    import httpx
    from datetime import date

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://localhost:7801/api/tasks/", params={"today": "true"})
            if resp.status_code != 200:
                return None
            data = resp.json()
            tasks = data.get("tasks", [])
            active = [t for t in tasks if t.get("status") != "done"]
            overdue = [t for t in active if t.get("due_date") and t["due_date"] <= date.today().isoformat()]

            if overdue:
                names = "、".join(t["title"][:20] for t in overdue[:3])
                return f"{len(overdue)} 个待办已到期：{names}"
            elif active:
                high = [t for t in active if t.get("priority") == "high"]
                if high:
                    return f"今天有 {len(high)} 个高优先级待办需处理"
                return f"今天有 {len(active)} 个待办待处理"
            else:
                return None  # 全完成了不需要汇报
    except Exception:
        return None


async def _task_conversation_recap() -> Optional[str]:
    """对话复盘（优化点5：结合用户事项分类框架）"""
    from .chat_db import list_conversations, get_conversation
    from .memory_db import get_all_profiles

    convs = list_conversations(limit=3)
    if not convs:
        return None

    recent_msgs = []
    for conv in convs[:2]:
        full = get_conversation(conv["id"])
        if full and full.get("messages"):
            for msg in full["messages"][-4:]:
                if msg["role"] == "user":
                    content = (msg.get("content") or "")[:100]
                    if content:
                        recent_msgs.append(content)

    if len(recent_msgs) < 2:
        return None  # 对话太少没有复盘价值

    # 获取用户画像来个性化复盘
    profiles = get_all_profiles()
    role_info = ""
    for p in profiles:
        if p["key"] in ("岗位", "职业", "身份", "角色"):
            role_info = f"用户是{p['value']}。"
            break

    from .chat_service import call_llm_simple
    prompt = f"""{role_info}分析用户最近的对话，提炼：
1. 用户当前关注什么（1句话）
2. 是否有未完成/等待中的事项（如有，列出）

用户的事项处理习惯：分为"直接执行/需确认/需讨论/阻塞/记录转出"五类。
如果能判断未完成事项属于哪类，请标注。

用户最近说的话：
{chr(10).join('- ' + m for m in recent_msgs[:8])}

请用 2-3 句话总结（不要敬语，平等语气）："""

    result = await call_llm_simple(prompt, max_tokens=150)
    return result.strip() if result else None


def _task_analyze_undos() -> Optional[str]:
    """撤回分析"""
    try:
        chat_conn = sqlite3.connect(str(PLATFORM_ROOT / "chat.db"))
        chat_conn.row_factory = sqlite3.Row
        count = chat_conn.execute(
            "SELECT COUNT(*) FROM messages WHERE active=0 AND role='assistant' "
            "AND created_at > datetime('now', '-7 days', 'localtime')"
        ).fetchone()[0]
        chat_conn.close()

        if count >= 3:  # 只有频繁撤回才值得报告
            return f"近 7 天有 {count} 次回答被撤回，需要关注回答质量"
        return None
    except Exception:
        return None


# 包装同步任务为 async
async def _task_analyze_undos_async() -> Optional[str]:
    return _task_analyze_undos()


# === 注册内置任务 ===
# priority: 越小越优先。10以下=紧急（冷却期内也执行）
register_idle_task("待办检查", _task_check_todos, priority=5, min_idle_minutes=0)
register_idle_task("对话复盘", _task_conversation_recap, priority=30, min_idle_minutes=60)
register_idle_task("撤回分析", _task_analyze_undos_async, priority=50, min_idle_minutes=120)


# === 汇报存储与读取 ===

def _save_report(tasks: list[dict]):
    """保存工作汇报"""
    summary_parts = [t["result"] for t in tasks if t.get("result")]
    summary = " | ".join(summary_parts) if summary_parts else "无特别发现"

    db = _get_db()
    db.execute(
        "INSERT INTO idle_reports (summary, tasks_executed) VALUES (?, ?)",
        (summary, json.dumps(tasks, ensure_ascii=False)),
    )
    db.commit()
    db.close()


def get_pending_report() -> Optional[dict]:
    """获取未展示的汇报（供 greeting API 调用）"""
    db = _get_db()
    row = db.execute(
        "SELECT * FROM idle_reports WHERE shown=0 ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if row:
        result = dict(row)
        result["tasks_executed"] = json.loads(result["tasks_executed"])
        db.execute("UPDATE idle_reports SET shown=1 WHERE id=?", (row["id"],))
        db.commit()
    else:
        result = None
    db.close()
    return result


def get_report_history(limit: int = 10) -> list[dict]:
    """获取汇报历史"""
    db = _get_db()
    rows = db.execute(
        "SELECT * FROM idle_reports ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    db.close()
    results = []
    for r in rows:
        item = dict(r)
        item["tasks_executed"] = json.loads(item["tasks_executed"])
        results.append(item)
    return results


# === 窗口 refocus 触发（优化点4）===

_last_focus_check: Optional[datetime] = None


async def on_window_focus():
    """
    前端窗口 refocus 时调用（通过 API）。
    如果距上次交互超过 30 分钟，立即检查是否有值得汇报的事。
    """
    global _last_focus_check
    now = datetime.now()

    # 防抖：10 秒内不重复触发
    if _last_focus_check and (now - _last_focus_check).total_seconds() < 10:
        return
    _last_focus_check = now

    idle_mins = get_idle_minutes()
    if idle_mins >= 30:
        # 用户离开超过 30 分钟回来了，立即跑一次紧急任务
        await check_and_run()
