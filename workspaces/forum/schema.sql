-- schema.sql — 岛主论坛 数据库设计
-- 创建时间: 2025-05-25
-- 说明: 缓存 Gitee Issues 数据，支持离线浏览

-- === 表: issues (Issue 缓存) ===
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY,
    number TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT DEFAULT '',
    state TEXT DEFAULT 'open',
    author TEXT DEFAULT '',
    labels TEXT DEFAULT '[]',
    comments_count INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT,
    synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- === 表: comments (评论缓存) ===
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY,
    issue_number TEXT NOT NULL,
    body TEXT NOT NULL,
    author TEXT DEFAULT '',
    created_at TEXT,
    synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- === 索引 ===
CREATE INDEX IF NOT EXISTS idx_issues_state ON issues(state);
CREATE INDEX IF NOT EXISTS idx_issues_updated ON issues(updated_at);
CREATE INDEX IF NOT EXISTS idx_comments_issue ON comments(issue_number);
