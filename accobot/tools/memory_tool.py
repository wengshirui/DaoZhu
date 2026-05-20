"""Memory & learning tools — remember user preferences, track knowledge.

Toolset: "memory"
Inspired by Hermes Agent's memory system, adapted for accounting domain.
Stores: user preferences, journal entry patterns, knowledge mastery.
"""

import json
import time
import uuid
from accobot.tools.registry import registry, tool_result, tool_error


def _get_master():
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    return mgr.master


def _ensure_memory_tables(master):
    """Create memory tables if they don't exist."""
    with master._lock:
        master._conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at REAL,
                updated_at REAL,
                use_count INTEGER DEFAULT 0
            )
        """)
        master._conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_points (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT,
                content TEXT,
                difficulty TEXT DEFAULT 'basic',
                source TEXT
            )
        """)
        master._conn.execute("""
            CREATE TABLE IF NOT EXISTS user_mastery (
                knowledge_point_id TEXT NOT NULL,
                status TEXT DEFAULT 'unlearned',
                first_seen_at REAL,
                last_reviewed_at REAL,
                review_count INTEGER DEFAULT 0,
                PRIMARY KEY (knowledge_point_id)
            )
        """)
        master._conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_cat ON memories(category)")
        master._conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key)")


# =========================================================================
# Memory CRUD
# =========================================================================

def remember(args: dict, **kwargs) -> str:
    """Store a memory (user preference, pattern, note)."""
    master = _get_master()
    _ensure_memory_tables(master)

    category = args.get("category", "preference")
    key = args.get("key", "").strip()
    value = args.get("value", "").strip()

    if not key:
        return tool_error("请指定要记住的内容标识")
    if not value:
        return tool_error("请指定要记住的内容")

    valid_categories = ("preference", "pattern", "note", "rule")
    if category not in valid_categories:
        category = "note"

    mem_id = uuid.uuid4().hex[:8]
    now = time.time()

    with master._lock:
        # Check if key already exists in this category
        cur = master._conn.execute(
            "SELECT id FROM memories WHERE category = ? AND key = ?", (category, key)
        )
        existing = cur.fetchone()
        if existing:
            master._conn.execute(
                "UPDATE memories SET value = ?, updated_at = ?, use_count = use_count + 1 WHERE id = ?",
                (value, now, existing["id"]),
            )
            return tool_result(success=True, message=f"已更新记忆：{key}")
        else:
            master._conn.execute(
                "INSERT INTO memories (id, category, key, value, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                (mem_id, category, key, value, now, now),
            )
            return tool_result(success=True, message=f"已记住：{key} = {value}")


def recall(args: dict, **kwargs) -> str:
    """Recall memories by category or keyword."""
    master = _get_master()
    _ensure_memory_tables(master)

    category = args.get("category")
    keyword = args.get("keyword", "")

    with master._lock:
        sql = "SELECT * FROM memories WHERE 1=1"
        params = []
        if category:
            sql += " AND category = ?"
            params.append(category)
        if keyword:
            sql += " AND (key LIKE ? OR value LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        sql += " ORDER BY updated_at DESC LIMIT 20"
        cur = master._conn.execute(sql, params)
        memories = [dict(row) for row in cur.fetchall()]

    if not memories:
        return tool_result(success=True, memories=[], message="没有找到相关记忆")

    lines = [f"记忆（{len(memories)} 条）："]
    for m in memories:
        lines.append(f"  [{m['category']}] {m['key']}：{m['value']}")

    return tool_result(success=True, memories=memories, message="\n".join(lines))


def forget(args: dict, **kwargs) -> str:
    """Delete a specific memory."""
    master = _get_master()
    _ensure_memory_tables(master)

    key = args.get("key", "").strip()
    if not key:
        return tool_error("请指定要忘记的内容")

    with master._lock:
        cur = master._conn.execute("DELETE FROM memories WHERE key LIKE ?", (f"%{key}%",))
        deleted = cur.rowcount

    if deleted == 0:
        return tool_result(success=True, message=f"没有找到关于「{key}」的记忆")
    return tool_result(success=True, message=f"已忘记 {deleted} 条关于「{key}」的记忆")


# =========================================================================
# Learning / Knowledge tracking
# =========================================================================

def record_learning(args: dict, **kwargs) -> str:
    """Record a knowledge point the user asked about."""
    master = _get_master()
    _ensure_memory_tables(master)

    title = args.get("title", "").strip()
    category = args.get("category", "accounting")
    content = args.get("content", "").strip()

    if not title:
        return tool_error("请指定知识点标题")

    kp_id = uuid.uuid4().hex[:8]
    now = time.time()

    with master._lock:
        # Check if already exists
        cur = master._conn.execute("SELECT id FROM knowledge_points WHERE title = ?", (title,))
        existing = cur.fetchone()
        if existing:
            kp_id = existing["id"]
        else:
            master._conn.execute(
                "INSERT INTO knowledge_points (id, title, category, content) VALUES (?,?,?,?)",
                (kp_id, title, category, content),
            )

        # Update mastery
        master._conn.execute(
            """INSERT OR REPLACE INTO user_mastery (knowledge_point_id, status, first_seen_at, last_reviewed_at, review_count)
               VALUES (?, 'aware',
                   COALESCE((SELECT first_seen_at FROM user_mastery WHERE knowledge_point_id = ?), ?),
                   ?,
                   COALESCE((SELECT review_count FROM user_mastery WHERE knowledge_point_id = ?), 0) + 1
               )""",
            (kp_id, kp_id, now, now, kp_id),
        )

    return tool_result(success=True, message=f"已记录知识点：{title}")


def learning_progress(args: dict, **kwargs) -> str:
    """Show user's learning progress."""
    master = _get_master()
    _ensure_memory_tables(master)

    with master._lock:
        cur = master._conn.execute("""
            SELECT kp.title, kp.category, um.status, um.review_count
            FROM knowledge_points kp
            LEFT JOIN user_mastery um ON kp.id = um.knowledge_point_id
            ORDER BY um.last_reviewed_at DESC
            LIMIT 20
        """)
        points = [dict(row) for row in cur.fetchall()]

    if not points:
        return tool_result(success=True, points=[], message="还没有学习记录")

    status_icons = {"unlearned": "⬜", "aware": "🟨", "mastered": "🟩"}
    lines = ["学习进度："]
    for p in points:
        icon = status_icons.get(p["status"] or "unlearned", "⬜")
        lines.append(f"  {icon} {p['title']}（{p['category']}）复习 {p['review_count'] or 0} 次")

    mastered = sum(1 for p in points if p["status"] == "mastered")
    aware = sum(1 for p in points if p["status"] == "aware")
    lines.insert(1, f"  已掌握 {mastered} | 学习中 {aware} | 总计 {len(points)}")

    return tool_result(success=True, points=points, message="\n".join(lines))


# =========================================================================
# Registration
# =========================================================================

registry.register(
    name="remember",
    toolset="memory",
    schema={
        "name": "remember",
        "description": "记住用户的偏好或规则。如用户说'记住快递费走邮寄费科目'、'我习惯用XX方式'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "类别：preference/pattern/note/rule"},
                "key": {"type": "string", "description": "标识（如：快递费科目）"},
                "value": {"type": "string", "description": "内容（如：管理费用-邮寄费 560210）"},
            },
            "required": ["key", "value"],
        },
    },
    handler=remember,
    emoji="🧠",
)

registry.register(
    name="recall",
    toolset="memory",
    schema={
        "name": "recall",
        "description": "回忆之前记住的内容。处理业务前先查看是否有相关记忆。",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "类别筛选"},
                "keyword": {"type": "string", "description": "关键词搜索"},
            },
        },
    },
    handler=recall,
    emoji="💭",
)

registry.register(
    name="forget",
    toolset="memory",
    schema={
        "name": "forget",
        "description": "忘记某条记忆。用户说'忘掉XX'、'删除关于XX的记忆'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "要忘记的内容关键词"},
            },
            "required": ["key"],
        },
    },
    handler=forget,
    emoji="🗑️",
)

registry.register(
    name="record_learning",
    toolset="memory",
    schema={
        "name": "record_learning",
        "description": "记录用户学到的知识点。当用户提问财务概念时自动调用，追踪学习进度。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "知识点标题（如：进项税额）"},
                "category": {"type": "string", "description": "分类：accounting/tax/law/practice"},
                "content": {"type": "string", "description": "知识点简要内容"},
            },
            "required": ["title"],
        },
    },
    handler=record_learning,
    emoji="📚",
)

registry.register(
    name="learning_progress",
    toolset="memory",
    schema={
        "name": "learning_progress",
        "description": "查看学习进度。用户问'我学了什么'、'学习记录'时使用。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=learning_progress,
    emoji="📊",
)
