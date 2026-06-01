CREATE TABLE IF NOT EXISTS prd_docs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT 'v1.0',
    status TEXT NOT NULL DEFAULT 'draft',
    author TEXT,
    product_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    summary TEXT,
    background TEXT,
    goals TEXT,
    target_users TEXT,
    milestones TEXT
);

CREATE TABLE IF NOT EXISTS prd_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prd_id INTEGER NOT NULL,
    section_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prd_id) REFERENCES prd_docs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS prd_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prd_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'P2',
    status TEXT NOT NULL DEFAULT '待评审',
    acceptance_criteria TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prd_id) REFERENCES prd_docs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS prd_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prd_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    definition TEXT NOT NULL DEFAULT '',
    target_value TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prd_id) REFERENCES prd_docs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS prd_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prd_id INTEGER NOT NULL,
    reviewer TEXT NOT NULL,
    comment TEXT NOT NULL DEFAULT '',
    decision TEXT NOT NULL DEFAULT '待定',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prd_id) REFERENCES prd_docs(id) ON DELETE CASCADE
);
