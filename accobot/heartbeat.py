"""Heartbeat — proactive background loop for reminders and checks.

Runs in a background thread, periodically checks for:
- Tax filing deadlines approaching
- Pending vouchers that need attention
- Accounting period close reminders

Pushes notifications to connected WebSocket clients.

Inspired by OpenClaw's heartbeat loop.
"""

import asyncio
import logging
import threading
import time
from datetime import date, timedelta
from typing import Any, Callable, Dict, List, Optional

from accobot.config import load_config

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_INTERVAL = 300  # 5 minutes
DEFAULT_ENABLED = True
REMINDER_DAYS_BEFORE = 5  # Remind N days before deadline


class Heartbeat:
    """Background heartbeat that checks for proactive notifications."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, on_notification: Optional[Callable] = None):
        cfg = config or load_config()
        hb_config = cfg.get("heartbeat", {})

        self.enabled = hb_config.get("enabled", DEFAULT_ENABLED)
        self.interval = hb_config.get("interval_minutes", 5) * 60
        self.on_notification = on_notification  # callback(type, message)

        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_check = 0.0

    def start(self) -> None:
        """Start the heartbeat background thread."""
        if not self.enabled:
            logger.debug("Heartbeat disabled in config")
            return
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="heartbeat")
        self._thread.start()
        logger.info("Heartbeat started (interval: %ds)", self.interval)

    def stop(self) -> None:
        """Stop the heartbeat."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None

    def _loop(self) -> None:
        """Main heartbeat loop."""
        # Wait a bit before first check (let the system initialize)
        time.sleep(10)

        while self._running:
            try:
                notifications = self._check()
                for notif in notifications:
                    if self.on_notification:
                        self.on_notification(notif["type"], notif["message"])
                self._last_check = time.time()
            except Exception as e:
                logger.debug("Heartbeat check error: %s", e)

            # Sleep in small increments so we can stop quickly
            for _ in range(int(self.interval)):
                if not self._running:
                    break
                time.sleep(1)

    def _check(self) -> List[Dict[str, str]]:
        """Run all checks and return notifications."""
        notifications = []

        # Tax deadline check
        tax_notifs = self._check_tax_deadlines()
        notifications.extend(tax_notifs)

        # Pending vouchers check
        voucher_notifs = self._check_pending_vouchers()
        notifications.extend(voucher_notifs)

        return notifications

    def _check_tax_deadlines(self) -> List[Dict[str, str]]:
        """Check for approaching tax deadlines."""
        notifications = []
        today = date.today()

        # Monthly tax deadlines (15th of each month)
        deadline_day = 15
        if today.day <= deadline_day:
            days_left = deadline_day - today.day
            if days_left <= REMINDER_DAYS_BEFORE and days_left > 0:
                notifications.append({
                    "type": "tax_reminder",
                    "message": f"⏰ 税务提醒：增值税/个税申报截止还有 {days_left} 天（{today.month}月{deadline_day}日）",
                })

        # Quarterly income tax (months 1,4,7,10)
        if today.month in (1, 4, 7, 10) and today.day <= deadline_day:
            days_left = deadline_day - today.day
            if days_left <= REMINDER_DAYS_BEFORE and days_left > 0:
                notifications.append({
                    "type": "tax_reminder",
                    "message": f"⏰ 税务提醒：企业所得税季度预缴截止还有 {days_left} 天",
                })

        # Annual business report (June 30)
        if today.month <= 6:
            deadline = date(today.year, 6, 30)
            days_left = (deadline - today).days
            if days_left <= 30 and days_left > 0:
                notifications.append({
                    "type": "business_reminder",
                    "message": f"⏰ 工商提醒：年报公示截止还有 {days_left} 天（6月30日）",
                })

        return notifications

    def _check_pending_vouchers(self) -> List[Dict[str, str]]:
        """Check for vouchers that need attention."""
        notifications = []
        try:
            from accobot.db.manager import DBManager
            mgr = DBManager.get_instance()
            if mgr.accounting:
                drafts = mgr.accounting.list_vouchers(status="draft", limit=100)
                if len(drafts) >= 5:
                    notifications.append({
                        "type": "voucher_reminder",
                        "message": f"📋 有 {len(drafts)} 张凭证待审核过账",
                    })
        except Exception:
            pass

        return notifications


# Module-level singleton
_heartbeat: Optional[Heartbeat] = None


def get_heartbeat() -> Heartbeat:
    """Get or create the heartbeat singleton."""
    global _heartbeat
    if _heartbeat is None:
        _heartbeat = Heartbeat()
    return _heartbeat


def start_heartbeat(on_notification: Optional[Callable] = None) -> None:
    """Start the global heartbeat."""
    global _heartbeat
    config = load_config()
    _heartbeat = Heartbeat(config=config, on_notification=on_notification)
    _heartbeat.start()


def stop_heartbeat() -> None:
    """Stop the global heartbeat."""
    if _heartbeat:
        _heartbeat.stop()
