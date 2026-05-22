"""Tests for proactive engine — REQ-019.

Verifies task registration, scheduling, one-shot completion, error isolation.
"""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def engine(tmp_path, monkeypatch):
    """Create a ProactiveEngine with isolated state."""
    monkeypatch.setenv("ACCOBOT_HOME", str(tmp_path))
    from accobot.proactive import ProactiveEngine
    return ProactiveEngine()


@pytest.fixture
def notification_cls():
    from accobot.proactive import Notification
    return Notification


@pytest.fixture
def task_cls():
    from accobot.proactive import ProactiveTask
    return ProactiveTask


class TestTaskRegistration:
    """Test task registration and basic properties."""

    def test_register_periodic_task(self, engine, task_cls):
        """AC-1: Can register a periodic task."""
        task = task_cls(
            name="test_periodic",
            trigger="periodic",
            interval_seconds=60,
            check_fn=lambda: [],
        )
        engine.register(task)
        assert "test_periodic" in engine._tasks

    def test_register_once_task(self, engine, task_cls):
        """AC-1: Can register a one-shot task."""
        task = task_cls(
            name="test_once",
            trigger="once",
            interval_seconds=0,
            check_fn=lambda: [],
        )
        engine.register(task)
        assert engine._tasks["test_once"].completed is False

    def test_register_on_start_task(self, engine, task_cls):
        """AC-1: Can register an on_start task."""
        task = task_cls(
            name="test_start",
            trigger="on_start",
            interval_seconds=0,
            check_fn=lambda: [],
        )
        engine.register(task)
        assert "test_start" in engine._tasks


class TestTaskExecution:
    """Test task execution and notification production."""

    def test_periodic_task_produces_notifications(self, engine, task_cls, notification_cls):
        """AC-2: Periodic task check_fn results become notifications."""
        notif = notification_cls(type="test", level="info", title="Test", message="Hello")

        task = task_cls(
            name="notifier",
            trigger="periodic",
            interval_seconds=60,
            check_fn=lambda: [notif],
        )
        engine.register(task)
        engine._execute_task(engine._tasks["notifier"])

        pending = engine.get_pending_notifications()
        assert len(pending) == 1
        assert pending[0].title == "Test"
        assert pending[0].task_name == "notifier"

    def test_once_task_marked_completed(self, engine, task_cls, tmp_path, monkeypatch):
        """AC-3: Once task is marked completed after execution."""
        monkeypatch.setenv("ACCOBOT_HOME", str(tmp_path))

        task = task_cls(
            name="setup_check",
            trigger="once",
            interval_seconds=0,
            check_fn=lambda: [],
        )
        engine.register(task)
        engine._execute_task(engine._tasks["setup_check"])

        assert engine._tasks["setup_check"].completed is True
        # Verify persisted
        state_path = tmp_path / ".proactive_state.json"
        assert state_path.exists()
        data = json.loads(state_path.read_text())
        assert "setup_check" in data["completed_tasks"]

    def test_completed_once_task_not_reregistered(self, tmp_path, monkeypatch, task_cls):
        """AC-3: Previously completed once task stays completed on re-register."""
        monkeypatch.setenv("ACCOBOT_HOME", str(tmp_path))

        # Write state file
        state_path = tmp_path / ".proactive_state.json"
        state_path.write_text(json.dumps({"completed_tasks": ["done_task"]}))

        from accobot.proactive import ProactiveEngine
        engine = ProactiveEngine()

        task = task_cls(
            name="done_task",
            trigger="once",
            interval_seconds=0,
            check_fn=lambda: [],
        )
        engine.register(task)
        assert engine._tasks["done_task"].completed is True


class TestErrorIsolation:
    """Test that task failures don't affect other tasks."""

    def test_failing_task_doesnt_crash_engine(self, engine, task_cls, notification_cls):
        """AC-5: A failing task doesn't prevent other tasks from running."""
        def failing_fn():
            raise RuntimeError("Boom!")

        good_notif = notification_cls(type="test", level="info", title="Good", message="OK")

        engine.register(task_cls(
            name="bad_task", trigger="periodic", interval_seconds=60,
            check_fn=failing_fn,
        ))
        engine.register(task_cls(
            name="good_task", trigger="periodic", interval_seconds=60,
            check_fn=lambda: [good_notif],
        ))

        # Execute both — bad one should not prevent good one
        engine._execute_task(engine._tasks["bad_task"])
        engine._execute_task(engine._tasks["good_task"])

        pending = engine.get_pending_notifications()
        assert len(pending) == 1
        assert pending[0].title == "Good"

    def test_empty_check_fn_no_notifications(self, engine, task_cls):
        """Edge case: check_fn returning empty list produces no notifications."""
        engine.register(task_cls(
            name="quiet", trigger="periodic", interval_seconds=60,
            check_fn=lambda: [],
        ))
        engine._execute_task(engine._tasks["quiet"])
        assert len(engine.get_pending_notifications()) == 0


class TestNotificationCallback:
    """Test on_notification callback."""

    def test_callback_called_on_notification(self, tmp_path, monkeypatch, task_cls, notification_cls):
        """AC-2: on_notification callback is invoked when notifications are produced."""
        monkeypatch.setenv("ACCOBOT_HOME", str(tmp_path))
        received = []

        from accobot.proactive import ProactiveEngine
        engine = ProactiveEngine(on_notification=lambda n: received.append(n))

        notif = notification_cls(type="test", level="warning", title="Alert", message="!")
        engine.register(task_cls(
            name="alerter", trigger="periodic", interval_seconds=60,
            check_fn=lambda: [notif],
        ))
        engine._execute_task(engine._tasks["alerter"])

        assert len(received) == 1
        assert received[0].title == "Alert"


class TestDefaultTasks:
    """Test the default financial tasks."""

    def test_create_default_engine(self, tmp_path, monkeypatch):
        """Default engine has tax and voucher tasks registered."""
        monkeypatch.setenv("ACCOBOT_HOME", str(tmp_path))
        from accobot.proactive import create_default_engine

        engine = create_default_engine()
        assert "tax_deadlines" in engine._tasks
        assert "pending_vouchers" in engine._tasks

    def test_tax_check_returns_list(self, tmp_path, monkeypatch):
        """Tax check function returns a list (may be empty)."""
        monkeypatch.setenv("ACCOBOT_HOME", str(tmp_path))
        from accobot.proactive import _check_tax_deadlines

        result = _check_tax_deadlines()
        assert isinstance(result, list)


class TestEnvironmentCheck:
    """Test first-run environment check (REQ-020)."""

    def test_check_environment_returns_list(self, tmp_path, monkeypatch):
        """AC-2: check_environment returns a list of notifications."""
        monkeypatch.setenv("ACCOBOT_HOME", str(tmp_path))
        from accobot.proactive import _check_environment

        result = _check_environment()
        assert isinstance(result, list)
        assert len(result) >= 1  # At least one notification (either issues or all-ok)

    def test_missing_api_key_produces_warning(self, tmp_path, monkeypatch):
        """AC-5: Missing API Key produces a warning notification."""
        monkeypatch.setenv("ACCOBOT_HOME", str(tmp_path))
        # Ensure no API key is set
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ACCOBOT_API_KEY", raising=False)

        from accobot.proactive import _check_environment

        result = _check_environment()
        api_notifs = [n for n in result if "API Key" in n.title]
        assert len(api_notifs) == 1
        assert api_notifs[0].level == "warning"

    def test_no_company_produces_action(self, tmp_path, monkeypatch):
        """AC-5: No account set produces an action notification."""
        monkeypatch.setenv("ACCOBOT_HOME", str(tmp_path))
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ACCOBOT_API_KEY", raising=False)

        from accobot.proactive import _check_environment

        result = _check_environment()
        company_notifs = [n for n in result if "账套" in n.title]
        assert len(company_notifs) == 1
        assert company_notifs[0].level == "action"
        assert company_notifs[0].action_prompt  # Has an action prompt

    def test_registered_as_once_task(self, tmp_path, monkeypatch):
        """AC-1: first_run_setup is registered as a once task in default engine."""
        monkeypatch.setenv("ACCOBOT_HOME", str(tmp_path))
        from accobot.proactive import create_default_engine

        engine = create_default_engine()
        assert "first_run_setup" in engine._tasks
        assert engine._tasks["first_run_setup"].trigger == "once"

    def test_once_task_not_rerun_after_completion(self, tmp_path, monkeypatch):
        """AC-1/AC-4: Once completed, first_run_setup doesn't run again."""
        monkeypatch.setenv("ACCOBOT_HOME", str(tmp_path))

        # Simulate previous completion
        state_path = tmp_path / ".proactive_state.json"
        state_path.write_text(json.dumps({"completed_tasks": ["first_run_setup"]}))

        from accobot.proactive import create_default_engine

        engine = create_default_engine()
        assert engine._tasks["first_run_setup"].completed is True
