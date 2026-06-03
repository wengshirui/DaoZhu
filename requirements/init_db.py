"""
需求管理数据库 — 初始化 + 从文件导入完整内容
运行: python requirements/init_db.py

已完成需求：从 done/*.md 读取完整内容存入 description
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
    created_at TEXT NOT NULL DEFAULT '',
    completed_at TEXT DEFAULT '',
    file_path TEXT DEFAULT '',
    description TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_req_status ON requirements(status);
CREATE INDEX IF NOT EXISTS idx_req_priority ON requirements(priority);
"""

# 已完成需求的时间估算（按开发顺序分批）
DONE_DATES = {
    # Phase 1: 项目初始化 (2026-05 上旬)
    1: ("2026-05-01", "2026-05-03"),
    2: ("2026-05-01", "2026-05-03"),
    3: ("2026-05-02", "2026-05-04"),
    4: ("2026-05-03", "2026-05-05"),
    5: ("2026-05-03", "2026-05-05"),
    6: ("2026-05-04", "2026-05-06"),
    7: ("2026-05-04", "2026-05-06"),
    8: ("2026-05-05", "2026-05-07"),
    10: ("2026-05-06", "2026-05-08"),
    11: ("2026-05-07", "2026-05-09"),
    # Phase 2: AccoBot + 记忆 (2026-05 中旬)
    12: ("2026-05-09", "2026-05-11"),
    13: ("2026-05-10", "2026-05-12"),
    14: ("2026-05-11", "2026-05-13"),
    15: ("2026-05-12", "2026-05-14"),
    16: ("2026-05-12", "2026-05-14"),
    17: ("2026-05-13", "2026-05-15"),
    18: ("2026-05-14", "2026-05-16"),
    # Phase 3: UI + 管理 (2026-05 中下旬)
    21: ("2026-05-15", "2026-05-17"),
    22: ("2026-05-15", "2026-05-17"),
    23: ("2026-05-16", "2026-05-18"),
    24: ("2026-05-16", "2026-05-18"),
    25: ("2026-05-17", "2026-05-19"),
    26: ("2026-05-17", "2026-05-19"),
    27: ("2026-05-18", "2026-05-20"),
    28: ("2026-05-18", "2026-05-20"),
    29: ("2026-05-19", "2026-05-21"),
    30: ("2026-05-19", "2026-05-21"),
    31: ("2026-05-20", "2026-05-22"),
    # Phase 4: 进程模型 + 配置 (2026-05 下旬)
    32: ("2026-05-21", "2026-05-23"),
    33: ("2026-05-21", "2026-05-23"),
    34: ("2026-05-22", "2026-05-24"),
    35: ("2026-05-22", "2026-05-24"),
    36: ("2026-05-23", "2026-05-25"),
    37: ("2026-05-23", "2026-05-25"),
    38: ("2026-05-24", "2026-05-26"),
    39: ("2026-05-24", "2026-05-26"),
    40: ("2026-05-25", "2026-05-27"),
    41: ("2026-05-25", "2026-05-27"),
    42: ("2026-05-26", "2026-05-28"),
    # Phase 5: 视觉 + Agent 进阶 (2026-05-27 ~ 05-29)
    44: ("2026-05-27", "2026-05-28"),
    45: ("2026-05-27", "2026-05-28"),
    47: ("2026-05-28", "2026-05-29"),
    49: ("2026-05-28", "2026-05-29"),
    50: ("2026-05-28", "2026-05-29"),
    51: ("2026-05-29", "2026-05-29"),
    # Phase 6: 桌面宠物 + Hermes 借鉴 (2026-05-29 ~ 06-02)
    48: ("2026-05-29", "2026-06-02"),
    52: ("2026-05-29", "2026-06-02"),
    53: ("2026-05-29", "2026-06-02"),
    54: ("2026-05-29", "2026-06-02"),
    56: ("2026-06-01", "2026-06-02"),
    57: ("2026-06-01", "2026-06-02"),
    58: ("2026-06-02", "2026-06-02"),
    59: ("2026-06-02", "2026-06-02"),
    60: ("2026-06-02", "2026-06-02"),
    65: ("2026-06-03", "2026-06-03"),
}


def _extract_id_from_filename(filename: str) -> int | None:
    match = re.match(r"^(\d+)", filename)
    return int(match.group(1)) if match else None


def _extract_title_from_content(content: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            title = line.lstrip("# ").strip()
            title = re.sub(r"^\d+\s*[—–-]\s*", "", title)
            return title
    return ""


def _extract_frontmatter(content: str) -> dict:
    info = {"priority": "P2", "size": "S", "created_at": ""}
    for line in content.splitlines()[:20]:
        if "优先级" in line or "Priority" in line.lower():
            match = re.search(r"P[0-3]", line)
            if match:
                info["priority"] = match.group(0)
        if "Size" in line or "size" in line.lower():
            match = re.search(r"\b(XS|S|M|L|XL)\b", line)
            if match:
                info["size"] = match.group(0)
        if "录入日期" in line or "创建" in line:
            match = re.search(r"(\d{4}-\d{2}-\d{2})", line)
            if match:
                info["created_at"] = match.group(1)
    return info


def import_done_files(conn: sqlite3.Connection) -> int:
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
        dates = DONE_DATES.get(req_id, ("2026-05-15", "2026-05-20"))
        created = info["created_at"] or dates[0]
        completed = dates[1]
        conn.execute(
            """INSERT OR REPLACE INTO requirements
               (id, title, status, priority, size, created_at, completed_at, description, file_path)
               VALUES (?, ?, 'done', ?, ?, ?, ?, ?, ?)""",
            (req_id, title, info["priority"], info["size"],
             created, completed, content, f"done/{md_file.name}"),
        )
        count += 1
    return count


def import_backlog_files(conn: sqlite3.Connection) -> int:
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
        created = info["created_at"] or "2026-06-03"

        # 检查是否已标记完成
        dates = DONE_DATES.get(req_id)
        if dates:
            conn.execute(
                """INSERT OR REPLACE INTO requirements
                   (id, title, status, priority, size, created_at, completed_at, description, file_path)
                   VALUES (?, ?, 'done', ?, ?, ?, ?, ?, ?)""",
                (req_id, title, info["priority"], info["size"],
                 created, dates[1], content, f"backlog/{md_file.name}"),
            )
        else:
            conn.execute(
                """INSERT OR IGNORE INTO requirements
                   (id, title, status, priority, size, created_at, file_path)
                   VALUES (?, ?, 'backlog', ?, ?, ?, ?)""",
                (req_id, title, info["priority"], info["size"],
                 created, f"backlog/{md_file.name}"),
            )
        count += 1
    return count


def import_cancelled(conn: sqlite3.Connection) -> int:
    conn.execute(
        """INSERT OR REPLACE INTO requirements
           (id, title, status, created_at, description)
           VALUES (19, '孕期管理 + 学习辅助', 'cancelled', '2026-05-10', '需求不明确，已取消')"""
    )
    return 1


def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(SCHEMA)

    done_count = import_done_files(conn)
    backlog_count = import_backlog_files(conn)
    cancelled_count = import_cancelled(conn)

    conn.commit()

    # 统计
    total = conn.execute("SELECT COUNT(*) FROM requirements").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM requirements WHERE status='done'").fetchone()[0]
    backlog = conn.execute("SELECT COUNT(*) FROM requirements WHERE status='backlog'").fetchone()[0]
    with_desc = conn.execute(
        "SELECT COUNT(*) FROM requirements WHERE description != ''"
    ).fetchone()[0]
    with_dates = conn.execute(
        "SELECT COUNT(*) FROM requirements WHERE created_at != ''"
    ).fetchone()[0]

    conn.close()

    print(f"✅ requirements.db 重建完成")
    print(f"   总计: {total} 条")
    print(f"   已完成: {done} | 待开发: {backlog} | 已取消: {cancelled_count}")
    print(f"   有完整内容: {with_desc} 条")
    print(f"   有日期信息: {with_dates} 条")


if __name__ == "__main__":
    init_db()
