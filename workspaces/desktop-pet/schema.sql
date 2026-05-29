-- schema.sql — 桌面宠物 数据库设计
-- 创建时间: 2026-05-29

-- === 表: pets (已下载的宠物) ===
CREATE TABLE IF NOT EXISTS pets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT,
    description TEXT,
    source_url TEXT,
    local_path TEXT NOT NULL,
    frame_width INTEGER DEFAULT 192,
    frame_height INTEGER DEFAULT 208,
    columns INTEGER DEFAULT 8,
    rows INTEGER DEFAULT 9,
    is_active INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- === 表: pet_state (宠物状态) ===
CREATE TABLE IF NOT EXISTS pet_state (
    pet_id INTEGER PRIMARY KEY REFERENCES pets(id) ON DELETE CASCADE,
    hunger INTEGER DEFAULT 100,
    thirst INTEGER DEFAULT 100,
    happiness INTEGER DEFAULT 100,
    energy INTEGER DEFAULT 100,
    last_fed_at DATETIME,
    last_watered_at DATETIME,
    last_interact_at DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- === 表: interactions (互动记录) ===
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER REFERENCES pets(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    value_change INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- === 表: settings (宠物设置) ===
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 默认设置
INSERT OR IGNORE INTO settings (key, value) VALUES
    ('roam_scope', 'workspace'),
    ('animation_fps', '8'),
    ('pet_scale', '1.0'),
    ('auto_decay', 'true'),
    ('decay_interval_minutes', '60');
