"""
需求管理数据库 — 初始化 + 从文件导入完整内容
运行: python requirements/init_db.py

已完成需求：从 done/*.md 读取完整内容存入 description 字段
待开发需求：只存元数据（内容在 backlog/*.md 中维护）
"""

import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).parent / "requirements.db"
DONE_DIR = Path(__file__).parent / "done"
BACKLOG_DIR = Path(__file__).parent / "backlog"

SCHEMA = """
DROP TABLE IF EXISTS requirements;

CREATE TABLE requirements (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'backlog'
        CHECK(status IN ('backlog', 'in_progress', 'done', 'cancelled')),
    priority TEXT DEFAULT 'P2'
        CHECK(priority IN ('P0', 'P1', 'P2', 'P3')),
    size TEXT DEFAULT 'S'
        CHECK(size IN ('XS', 'S', 'M', 'L', 'XL')),
    created_at TEXT,
    completed_at TEXT,
    tags TEXT DEFAULT '',
    file_path TEXT DEFAULT '',
    description TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_req_status ON requirements(status);
CREATE INDEX IF NOT EXISTS idx_req_priority ON requirements(priority);
"""


def _extract_id_from_filename(filename: str) -> int | None:
    """从文件名提取需求 ID，如 '052-desktop-pet-workspace.md' → 52"""
    match = re.match(r"^(\d+)", filename)
    return int(match.group(1)) if match else None


def _extract_title_from_content(content: str) -> str:
    """从 markdown 内容提取标题（第一个 # 行）"""
    for line in content.splitlines():
        if line.startswith("# "):
            # 去掉 ID 前缀，如 "# 052 — 桌面宠物工作区" → "桌面宠物工作区"
            title = line.lstrip("# ").strip()
            # 去掉 "052 — " 前缀
            title = re.sub(r"^\d+\s*[—–-]\s*", "", title)
            return title
    return ""


def _extract_frontmatter(content: str) -> dict:
    """从需求文档提取 frontmatter 信息"""
    info = {"priority": "P2", "size": "S"}
    for line in content.splitlines()[:20]:
        if "优先级" in line or "Priority" in line.lower():
            match = re.search(r"P[0-3]", line)
            if match:
                info["priority"] = match.group(0)
        if "Size" in line or "size" in line.lower():
            match = re.search(r"\b(XS|S|M|L|XL)\b", line)
            if match:
                info["size"] = match.group(0)
    return info


def import_done_files(conn: sqlite3.Connection):
    """从 done/ 目录导入已完成需求（完整内容存入 description）"""
    if not DONE_DIR.exists():
        return 0

    count = 0
    for md_file in sorted(DONE_DIR.glob("*.md")):
        req_id = _extract_id_from_filename(md_file.name)
        if req_id is None:
            continue

        content = md_file.read_text(encoding="utf-8")
        title = _extract_title_from_content(content) or md_file.stem
        info = _extract_frontmatter(content)

        conn.execute(
            """INSERT OR REPLACE INTO requirements
               (id, title, status, priority, size, description, file_path)
               VALUES (?, ?, 'done', ?, ?, ?, ?)""",
            (req_id, title, info["priority"], info["size"], content, f"done/{md_file.name}"),
        )
        count += 1

    return count


def import_backlog_files(conn: sqlite3.Connection):
    """从 backlog/ 目录导入待开发需求（只存元数据，不存完整内容）"""
    if not BACKLOG_DIR.exists():
        return 0

    count = 0
    for md_file in sorted(BACKLOG_DIR.glob("*.md")):
        req_id = _extract_id_from_filename(md_file.name)
        if req_id is None:
            continue

        content = md_file.read_text(encoding="utf-8")
        title = _extract_title_from_content(content) or md_file.stem
        info = _extract_frontmatter(content)

        # backlog 只存元数据（description 留空，内容在 md 文件里维护）
        conn.execute(
            """INSERT OR IGNORE INTO requirements
               (id, title, status, priority, size, file_path)
               VALUES (?, ?, 'backlog', ?, ?, ?)""",
            (req_id, title, info["priority"], info["size"], f"backlog/{md_file.name}"),
        )
        count += 1

    return count


def import_extra_done(conn: sqlite3.Connection):
    """导入没有 done/*.md 文件但在 plan.md 中标记完成的需求"""
    # 这些需求完成了但没有单独的 done/ 文件（较新的需求直接在 backlog/ 中）
    extra = [
        (48, "用户手动绑定文件夹为工作区"),
        (52, "桌面宠物工作区"),
        (53, "Agent 分层解决策略"),
        (54, "Agent Python 兜底策略"),
        (56, "消息撤回（软删除 + Undo）"),
        (57, "消息防抖批处理"),
        (58, "DeepSeek 前缀缓存优化"),
        (59, "会话自动压缩"),
        (60, "工具调用权限门控"),
        (65, "需求管理数据化（SQLite 存储）"),
    ]

    count = 0
    for req_id, title in extra:
        # 尝试从 backlog/ 读取内容
        desc = ""
        for md_file in BACKLOG_DIR.glob(f"{req_id:03d}-*.md"):
            desc = md_file.read_text(encoding="utf-8")
            break

        conn.execute(
            """INSERT OR REPLACE INTO requirements
               (id, title, status, priority, size, description, completed_at)
               VALUES (?, ?, 'done', 'P1', 'S', ?, '2026-06-02')""",
            (req_id, title, desc),
        )
        count += 1

    return count


def import_cancelled(conn: sqlite3.Connection):
    """导入已取消需求"""
    conn.execute(
        """INSERT OR REPLACE INTO requirements (id, title, status, description)
           VALUES (19, '孕期管理 + 学习辅助', 'cancelled', '需求不明确，已取消')"""
    )
    return 1


def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(SCHEMA)

    done_count = import_done_files(conn)
    backlog_count = import_backlog_files(conn)
    extra_count = import_extra_done(conn)
    cancelled_count = import_cancelled(conn)

    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM requirements").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM requirements WHERE status='done'").fetchone()[0]
    backlog = conn.execute("SELECT COUNT(*) FROM requirements WHERE status='backlog'").fetchone()[0]
    with_desc = conn.execute(
        "SELECT COUNT(*) FROM requirements WHERE description != ''"
    ).fetchone()[0]

    conn.close()

    print(f"✅ requirements.db 初始化完成")
    print(f"   总计: {total} 条")
    print(f"   已完成: {done}（含完整内容: {with_desc}）")
    print(f"   待开发: {backlog}")
    print(f"   已取消: {cancelled_count}")
    print(f"")
    print(f"   导入来源:")
    print(f"   - done/*.md: {done_count} 条（完整内容）")
    print(f"   - backlog/*.md: {backlog_count} 条（元数据）")
    print(f"   - 补充已完成: {extra_count} 条")


if __name__ == "__main__":
    init_db()
