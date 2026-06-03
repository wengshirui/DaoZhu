"""
需求管理数据库 — 初始化 + 数据导入
运行: python requirements/init_db.py
"""

import sqlite3
from pathlib import Path
from datetime import date

DB_PATH = Path(__file__).parent / "requirements.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS requirements (
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

# 从 plan.md 提取的已完成需求
DONE_REQUIREMENTS = [
    (1, "主界面前端（三栏布局）"),
    (2, "默认工具与技能"),
    (3, "create-workspaces 技能"),
    (4, "工作区进程管理"),
    (5, "平台全局配置"),
    (6, "平台级 AI Agent"),
    (7, "AI 对话后端"),
    (8, "工作区代码生成"),
    (10, "工作区模板规范"),
    (11, "打包分发（轻量启动器）"),
    (12, "AccoBot 适配迁移"),
    (13, "对话记忆与 Skill 优化"),
    (14, "用户引导页面"),
    (15, "像素岛管理员形象"),
    (16, "UI 修复（字体/折叠/favicon）"),
    (17, "管家操作工作区数据"),
    (18, "好玩（发现的快乐 + KAPLAY）"),
    (21, "资源 README 展示"),
    (22, "未配置自动跳转引导"),
    (23, "工作区隐藏（软删除）"),
    (24, "实体 CRUD 规范"),
    (25, "岛主论坛对接 Gitee Issues"),
    (26, "工作区拖动排序"),
    (27, "岛管理员改名"),
    (28, "AI 根据记忆自动优化资源"),
    (29, "AI 工作状态 + 打断输出"),
    (30, "README 页打开按钮"),
    (31, "设置页面"),
    (32, "三层进程模型（轻量/标准/重型）"),
    (33, "创建进度记录 + 断点续做"),
    (34, "删除类操作用户确认"),
    (35, "工具/技能禁用 + 排序"),
    (36, "岛屿命名 + 愿景"),
    (37, "配置统一存储到 SQLite"),
    (38, "技能/工具删除功能"),
    (39, "Playwright MCP 兜底"),
    (40, "AI 自我优化机制"),
    (41, "项目速度优化"),
    (42, "论坛 Issue 详情和评论"),
    (44, "火柴人剧场（AutoMovie）"),
    (45, "多模型 Provider（Ollama/智谱/OpenAI）"),
    (47, "岛主主页视觉优化"),
    (48, "用户手动绑定文件夹为工作区"),
    (49, "工具调用可视化（指挥官体验）"),
    (50, "工具调用记录持久化"),
    (51, "多角色 Agent（调度/执行/质检）"),
    (52, "桌面宠物工作区"),
    (53, "Agent 分层解决策略"),
    (54, "Agent Python 兜底策略"),
    (56, "消息撤回（软删除 + Undo）"),
    (57, "消息防抖批处理"),
    (58, "DeepSeek 前缀缓存优化"),
    (59, "会话自动压缩"),
    (60, "工具调用权限门控"),
]

# 当前 backlog 需求
BACKLOG_REQUIREMENTS = [
    (46, "火柴人剧场 BGM + 配音", "P0", "M"),
    (61, "对话 Token 消耗 + 速度显示", "P1", "S"),
    (62, "AI 定时自我复盘（记忆 + 日志）", "P1", "M"),
    (63, "智能模型路由（大模型带小模型）", "P1", "M"),
    (64, "AI 主动交互（评估需求 + 主动提问）", "P1", "M"),
    (65, "需求管理数据化（SQLite 存储）", "P2", "S"),
    (66, "Gitee 生态架构（四仓库体系）", "P1", "L"),
    (20, "本地性能检测 + 智能推荐", "P2", "S"),
    (55, "待办今日聚焦桌面侧边栏", "P3", "M"),
]

# 已取消
CANCELLED = [
    (19, "孕期管理 + 学习辅助"),
]


def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(SCHEMA)

    # 导入已完成
    for req_id, title in DONE_REQUIREMENTS:
        conn.execute(
            """INSERT OR IGNORE INTO requirements (id, title, status)
               VALUES (?, ?, 'done')""",
            (req_id, title),
        )

    # 导入 backlog
    for req_id, title, priority, size in BACKLOG_REQUIREMENTS:
        conn.execute(
            """INSERT OR IGNORE INTO requirements (id, title, status, priority, size)
               VALUES (?, ?, 'backlog', ?, ?)""",
            (req_id, title, priority, size),
        )

    # 导入已取消
    for req_id, title in CANCELLED:
        conn.execute(
            """INSERT OR IGNORE INTO requirements (id, title, status)
               VALUES (?, ?, 'cancelled')""",
            (req_id, title),
        )

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM requirements").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM requirements WHERE status='done'").fetchone()[0]
    backlog = conn.execute("SELECT COUNT(*) FROM requirements WHERE status='backlog'").fetchone()[0]
    conn.close()

    print(f"✅ requirements.db 初始化完成")
    print(f"   总计: {total} 条 | 已完成: {done} | 待开发: {backlog}")


if __name__ == "__main__":
    init_db()
