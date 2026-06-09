"""
岛主 Agent 准确性测试 — 问题库
每个问题有独立的 verify() 获取真实答案。
不断新增问题即可扩展测试覆盖面。
"""

import re
import sqlite3
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).parent.parent
TODO_DB = ROOT / "workspaces" / "todo" / "data.db"
PET_DB = ROOT / "workspaces" / "desktop-pet" / "data.db"


def _count_db(db_path: Path, sql: str) -> int:
    conn = sqlite3.connect(str(db_path))
    count = conn.execute(sql).fetchone()[0]
    conn.close()
    return count


class Question:
    def __init__(self, id: str, text: str, verify_fn, match_fn=None):
        self.id = id
        self.text = text
        self.verify_fn = verify_fn
        self.match_fn = match_fn or self._default_match

    def verify(self):
        return self.verify_fn()

    def match(self, response: str, truth) -> bool:
        return self.match_fn(response, truth)

    def _default_match(self, response: str, truth) -> bool:
        if isinstance(truth, int):
            return str(truth) in response
        if isinstance(truth, str):
            return truth.lower() in response.lower()
        return False


# === 问题库 ===

QUESTIONS = [
    # --- 待办相关 ---
    Question(
        id="todo_total",
        text="我一共有多少个待办任务？帮我查一下",
        verify_fn=lambda: _count_db(TODO_DB, "SELECT COUNT(*) FROM tasks"),
    ),
    Question(
        id="todo_active",
        text="查一下我有几个未完成的待办",
        verify_fn=lambda: _count_db(TODO_DB, "SELECT COUNT(*) FROM tasks WHERE status != 'done'"),
    ),
    Question(
        id="todo_done",
        text="我完成了几个待办任务？",
        verify_fn=lambda: _count_db(TODO_DB, "SELECT COUNT(*) FROM tasks WHERE status = 'done'"),
    ),
    Question(
        id="todo_today",
        text="今天有几个到期的待办？",
        verify_fn=lambda: _count_db(
            TODO_DB,
            f"SELECT COUNT(*) FROM tasks WHERE due_date = '{date.today().isoformat()}' AND status != 'done'"
        ),
        match_fn=lambda resp, truth: str(truth) in resp or (truth == 0 and ("没有" in resp or "0" in resp or "无" in resp)),
    ),
    Question(
        id="todo_projects",
        text="待办工作区里一共有几个分类（项目）？",
        verify_fn=lambda: _count_db(TODO_DB, "SELECT COUNT(*) FROM projects"),
    ),
    Question(
        id="todo_high_priority",
        text="我有几个高优先级的待办？",
        verify_fn=lambda: _count_db(TODO_DB, "SELECT COUNT(*) FROM tasks WHERE priority = 'high' AND status != 'done'"),
    ),

    # --- 工作区相关 ---
    Question(
        id="workspace_count",
        text="帮我看看我有几个工作区",
        verify_fn=lambda: len([
            d for d in (ROOT / "workspaces").iterdir()
            if d.is_dir() and (d / "workspace.json").exists()
            and not _is_hidden_workspace(d)
        ]),
    ),

    # --- 文件相关 ---
    Question(
        id="file_lines_prompts",
        text="daozhu/prompts.py 这个文件一共有多少行？",
        verify_fn=lambda: len((ROOT / "daozhu" / "prompts.py").read_text(encoding="utf-8").splitlines()),
    ),
    Question(
        id="file_lines_agent",
        text="daozhu/agent.py 一共有多少行代码？",
        verify_fn=lambda: len((ROOT / "daozhu" / "agent.py").read_text(encoding="utf-8").splitlines()),
    ),

    # --- 时间相关 ---
    Question(
        id="time_hour",
        text="现在是几点？",
        verify_fn=lambda: datetime.now().hour,
        match_fn=lambda resp, truth: str(truth) in resp,
    ),

    # --- 宠物相关 ---
    Question(
        id="pet_count",
        text="我现在有几个桌面宠物？",
        verify_fn=lambda: _count_db(PET_DB, "SELECT COUNT(*) FROM pets") if PET_DB.exists() else 0,
        match_fn=lambda resp, truth: str(truth) in resp or (truth == 0 and ("没有" in resp or "0" in resp)),
    ),
]


def _is_hidden_workspace(ws_path: Path) -> bool:
    """检查工作区是否被隐藏"""
    import json
    ws_json = ws_path / "workspace.json"
    if not ws_json.exists():
        return False
    try:
        data = json.loads(ws_json.read_text(encoding="utf-8"))
        return data.get("hidden", False)
    except Exception:
        return False
