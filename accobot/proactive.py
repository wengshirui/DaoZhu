"""Proactive task engine — register and schedule background checks.

Replaces the simple Heartbeat with a general-purpose task framework.
Tasks can be periodic (tax reminders), one-shot (first-run setup),
or on-start (environment check).

All tasks produce Notifications — never execute write operations directly.
Write operations require user confirmation via the UI.

REQ-019: Agent 主动任务机制
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from accobot.config import get_accobot_home

logger = logging.getLogger(__name__)

# Persistent state file for one-shot task completion
STATE_FILE = ".proactive_state.json"


@dataclass
class Notification:
    """A notification produced by a proactive task."""
    type: str             # e.g. "tax_reminder", "voucher_reminder", "system"
    level: str            # "info" | "warning" | "action"
    title: str            # Short title for display
    message: str          # Detailed message
    action_prompt: str = ""  # If level=="action", prompt to send to Agent on confirm
    task_name: str = ""   # Which task produced this
    timestamp: float = field(default_factory=time.time)


@dataclass
class ProactiveTask:
    """A registered proactive task."""
    name: str
    trigger: str          # "periodic" | "once" | "on_start"
    interval_seconds: int  # For periodic tasks (ignored for once/on_start)
    check_fn: Callable[[], List[Notification]]
    completed: bool = False
    last_run: float = 0.0


class ProactiveEngine:
    """Manages proactive task registration, scheduling, and notification delivery."""

    def __init__(self, on_notification: Optional[Callable[[Notification], None]] = None):
        self._tasks: Dict[str, ProactiveTask] = {}
        self._notifications: List[Notification] = []
        self._on_notification = on_notification
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # Load completed state
        self._completed_tasks = self._load_state()

    def register(self, task: ProactiveTask) -> None:
        """Register a proactive task."""
        # Mark as completed if previously done (for once tasks)
        if task.trigger == "once" and task.name in self._completed_tasks:
            task.completed = True
        self._tasks[task.name] = task
        logger.debug("Registered proactive task: %s (trigger=%s)", task.name, task.trigger)

    def start(self) -> None:
        """Start the proactive engine background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="proactive-engine")
        self._thread.start()
        logger.info("ProactiveEngine started with %d task(s)", len(self._tasks))

    def stop(self) -> None:
        """Stop the engine."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None

    def mark_completed(self, task_name: str) -> None:
        """Mark a one-shot task as completed (persisted)."""
        task = self._tasks.get(task_name)
        if task:
            task.completed = True
        self._completed_tasks.add(task_name)
        self._save_state()

    def get_pending_notifications(self) -> List[Notification]:
        """Return all pending notifications (thread-safe)."""
        with self._lock:
            return list(self._notifications)

    def clear_notifications(self) -> None:
        """Clear all pending notifications."""
        with self._lock:
            self._notifications.clear()

    def dismiss_notification(self, index: int) -> bool:
        """Dismiss a specific notification by index."""
        with self._lock:
            if 0 <= index < len(self._notifications):
                self._notifications.pop(index)
                return True
            return False

    # =========================================================================
    # Internal
    # =========================================================================

    def _loop(self) -> None:
        """Main scheduling loop."""
        # Initial delay to let the system initialize
        time.sleep(5)

        # Run on_start tasks immediately
        self._run_on_start_tasks()

        while self._running:
            now = time.time()

            for task in list(self._tasks.values()):
                if task.completed:
                    continue

                should_run = False

                if task.trigger == "periodic":
                    if now - task.last_run >= task.interval_seconds:
                        should_run = True
                elif task.trigger == "once":
                    if task.last_run == 0:
                        should_run = True

                if should_run:
                    self._execute_task(task)

            # Sleep in small increments for responsive shutdown
            for _ in range(10):
                if not self._running:
                    break
                time.sleep(1)

    def _run_on_start_tasks(self) -> None:
        """Execute all on_start tasks once."""
        for task in list(self._tasks.values()):
            if task.trigger == "on_start" and not task.completed:
                self._execute_task(task)

    def _execute_task(self, task: ProactiveTask) -> None:
        """Execute a single task with error isolation."""
        try:
            notifications = task.check_fn()
            task.last_run = time.time()

            if notifications:
                for notif in notifications:
                    notif.task_name = task.name
                    with self._lock:
                        self._notifications.append(notif)
                    if self._on_notification:
                        try:
                            self._on_notification(notif)
                        except Exception as e:
                            logger.debug("Notification callback error: %s", e)

            # Mark once tasks as completed after successful run
            if task.trigger == "once":
                self.mark_completed(task.name)

        except Exception as e:
            logger.warning("Proactive task '%s' failed: %s", task.name, e)
            # Error isolation: task failure doesn't affect others

    # =========================================================================
    # State Persistence
    # =========================================================================

    def _get_state_path(self) -> Path:
        return get_accobot_home() / STATE_FILE

    def _load_state(self) -> set:
        """Load completed task names from disk."""
        path = self._get_state_path()
        if not path.exists():
            return set()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return set(data.get("completed_tasks", []))
        except Exception:
            return set()

    def _save_state(self) -> None:
        """Persist completed task names to disk."""
        path = self._get_state_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {"completed_tasks": sorted(self._completed_tasks)}
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.debug("Failed to save proactive state: %s", e)


# =========================================================================
# Default Tasks (migrated from heartbeat.py)
# =========================================================================

def _check_tax_deadlines() -> List[Notification]:
    """Check for approaching tax deadlines."""
    from datetime import date
    notifications = []
    today = date.today()
    REMINDER_DAYS = 5

    # Monthly tax deadlines (15th)
    deadline_day = 15
    if today.day <= deadline_day:
        days_left = deadline_day - today.day
        if 0 < days_left <= REMINDER_DAYS:
            notifications.append(Notification(
                type="tax_reminder",
                level="warning",
                title="增值税/个税申报",
                message=f"申报截止还有 {days_left} 天（{today.month}月{deadline_day}日）",
                action_prompt="帮我看看这个月的增值税和个税要交多少",
            ))

    # Quarterly income tax
    if today.month in (1, 4, 7, 10) and today.day <= deadline_day:
        days_left = deadline_day - today.day
        if 0 < days_left <= REMINDER_DAYS:
            notifications.append(Notification(
                type="tax_reminder",
                level="warning",
                title="企业所得税季度预缴",
                message=f"截止还有 {days_left} 天",
                action_prompt="帮我算一下本季度企业所得税预缴金额",
            ))

    # Annual business report (June 30)
    if today.month <= 6:
        deadline = date(today.year, 6, 30)
        days_left = (deadline - today).days
        if 0 < days_left <= 30:
            notifications.append(Notification(
                type="business_reminder",
                level="info",
                title="工商年报公示",
                message=f"截止还有 {days_left} 天（6月30日）",
            ))

    return notifications


def _check_pending_vouchers() -> List[Notification]:
    """Check for vouchers needing attention."""
    notifications = []
    try:
        from accobot.db.manager import DBManager
        mgr = DBManager.get_instance()
        if mgr.accounting:
            drafts = mgr.accounting.list_vouchers(status="draft", limit=100)
            if len(drafts) >= 5:
                notifications.append(Notification(
                    type="voucher_reminder",
                    level="action",
                    title=f"{len(drafts)} 张凭证待过账",
                    message=f"有 {len(drafts)} 张凭证处于草稿状态，建议审核过账",
                    action_prompt="帮我把所有草稿凭证过账",
                ))
    except Exception:
        pass
    return notifications


def _check_environment() -> List[Notification]:
    """First-run environment check (REQ-020).

    Checks: Node.js/npx, browser, API Key, account set.
    Produces notifications for missing items.
    """
    import os
    import shutil
    import sys

    notifications = []
    all_ok = True

    # 1. Check Node.js / npx (needed for Playwright MCP)
    node = shutil.which("node")
    npx = shutil.which("npx")
    if not node or not npx:
        all_ok = False
        notifications.append(Notification(
            type="system",
            level="warning",
            title="未检测到 Node.js",
            message="浏览器自动化功能（报税、开票）需要 Node.js。请安装 Node.js LTS 版本。",
            action_prompt="帮我检查一下 Node.js 环境，如果没有的话告诉我怎么安装",
        ))

    # 2. Check browser availability
    browser_found = False
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        for path in candidates:
            if os.path.isfile(path):
                browser_found = True
                break
    if not browser_found:
        # Also check via which
        for name in ["chrome", "chromium", "msedge", "google-chrome"]:
            if shutil.which(name):
                browser_found = True
                break

    if not browser_found and not npx:
        # Only warn if npx also missing (Playwright can download its own browser)
        all_ok = False
        notifications.append(Notification(
            type="system",
            level="info",
            title="未检测到浏览器",
            message="建议安装 Chrome 或 Edge 浏览器，用于自动化报税和开票操作。",
        ))

    # 3. Check API Key
    from accobot.config import load_env, get_api_key
    load_env()
    if not get_api_key():
        all_ok = False
        notifications.append(Notification(
            type="system",
            level="warning",
            title="未配置 API Key",
            message="请在设置中配置 DeepSeek 或 OpenAI 的 API Key，否则无法使用 AI 对话功能。",
            action_prompt="",  # No agent action — user needs to open settings
        ))

    # 4. Check if any company/account set exists
    try:
        from accobot.db.manager import DBManager
        mgr = DBManager.get_instance()
        companies = mgr.master.list_companies()
        if not companies:
            all_ok = False
            notifications.append(Notification(
                type="system",
                level="action",
                title="尚未创建账套",
                message="创建一个账套后即可开始记账。点击左侧「+ 新建」或告诉我公司名称。",
                action_prompt="帮我创建一个新账套",
            ))
    except Exception:
        pass

    # All good
    if all_ok:
        notifications.append(Notification(
            type="system",
            level="info",
            title="环境就绪",
            message="✅ 所有环境检测通过，AccoBot 已准备就绪！",
        ))

    return notifications


def create_default_engine(on_notification=None) -> ProactiveEngine:
    """Create a ProactiveEngine with default financial tasks registered."""
    engine = ProactiveEngine(on_notification=on_notification)

    # Tax deadline check (every 6 hours)
    engine.register(ProactiveTask(
        name="tax_deadlines",
        trigger="periodic",
        interval_seconds=6 * 3600,
        check_fn=_check_tax_deadlines,
    ))

    # Pending vouchers check (every 30 minutes)
    engine.register(ProactiveTask(
        name="pending_vouchers",
        trigger="periodic",
        interval_seconds=30 * 60,
        check_fn=_check_pending_vouchers,
    ))

    # First-run environment setup (REQ-020) — once only
    engine.register(ProactiveTask(
        name="first_run_setup",
        trigger="once",
        interval_seconds=0,
        check_fn=_check_environment,
    ))

    return engine


# =========================================================================
# Module-level singleton (backward compatible with heartbeat API)
# =========================================================================

_engine: Optional[ProactiveEngine] = None


def get_engine() -> ProactiveEngine:
    """Get or create the proactive engine singleton."""
    global _engine
    if _engine is None:
        _engine = create_default_engine()
    return _engine


def start_proactive(on_notification=None) -> None:
    """Start the proactive engine (replaces start_heartbeat)."""
    global _engine
    _engine = create_default_engine(on_notification=on_notification)
    _engine.start()


def stop_proactive() -> None:
    """Stop the proactive engine."""
    if _engine:
        _engine.stop()
