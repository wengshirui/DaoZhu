-- schema.sql — 需求池管理 数据库设计
-- 系统表 + 需求表（两级管理）

CREATE TABLE IF NOT EXISTS systems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    system_id INTEGER NOT NULL,
    port TEXT NOT NULL DEFAULT 'web' CHECK(port IN ('web','移动端','web+移动端','android','ios')),
    module TEXT DEFAULT '',
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    source TEXT DEFAULT '产品' CHECK(source IN ('领导','业务','产品','测试','实施')),
    priority INTEGER DEFAULT 2 CHECK(priority IN (1,2,3)),
    proposer TEXT DEFAULT '',
    propose_date TEXT DEFAULT '',
    plan_date TEXT DEFAULT '',
    status TEXT DEFAULT '进入需求池' CHECK(status IN ('进入需求池','待论证','待设计','设计中','交付UI','开发中','已上线','已关闭')),
    plan_version TEXT DEFAULT '',
    actual_version TEXT DEFAULT '',
    online_date TEXT DEFAULT '',
    remark TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (system_id) REFERENCES systems(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_requirements_system ON requirements(system_id);
CREATE INDEX IF NOT EXISTS idx_requirements_status ON requirements(status);
CREATE INDEX IF NOT EXISTS idx_requirements_priority ON requirements(priority);
CREATE INDEX IF NOT EXISTS idx_requirements_source ON requirements(source);
CREATE INDEX IF NOT EXISTS idx_requirements_port ON requirements(port);
