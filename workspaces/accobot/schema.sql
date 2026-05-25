-- schema.sql — 财务助手 数据库设计
-- 创建时间: 2025-05-25
-- 来源: AccoBot 核心财务模型

-- === 表: companies (公司/账套) ===
-- 用途: 管理多个公司的财务数据
CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT DEFAULT '',
    taxpayer_type TEXT DEFAULT 'small_scale',
    accounting_standard TEXT DEFAULT 'small_enterprise',
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- === 表: accounts (会计科目) ===
-- 用途: 科目表，支持树形结构
CREATE TABLE IF NOT EXISTS accounts (
    code TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    balance_direction TEXT DEFAULT 'debit',
    parent_code TEXT,
    is_leaf INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- === 表: periods (会计期间) ===
-- 用途: 管理会计年度和月份
CREATE TABLE IF NOT EXISTS periods (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- === 表: vouchers (凭证) ===
-- 用途: 记账凭证头
CREATE TABLE IF NOT EXISTS vouchers (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    voucher_date TEXT NOT NULL,
    period_id TEXT,
    summary TEXT DEFAULT '',
    status TEXT DEFAULT 'draft',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (period_id) REFERENCES periods(id)
);

-- === 表: entries (分录) ===
-- 用途: 凭证明细行（借贷分录）
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_id TEXT NOT NULL,
    account_code TEXT NOT NULL,
    summary TEXT DEFAULT '',
    debit REAL DEFAULT 0,
    credit REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (voucher_id) REFERENCES vouchers(id) ON DELETE CASCADE,
    FOREIGN KEY (account_code) REFERENCES accounts(code)
);

-- === 索引 ===
CREATE INDEX IF NOT EXISTS idx_accounts_company ON accounts(company_id);
CREATE INDEX IF NOT EXISTS idx_accounts_category ON accounts(category);
CREATE INDEX IF NOT EXISTS idx_periods_company ON periods(company_id);
CREATE INDEX IF NOT EXISTS idx_vouchers_company ON vouchers(company_id);
CREATE INDEX IF NOT EXISTS idx_vouchers_date ON vouchers(voucher_date);
CREATE INDEX IF NOT EXISTS idx_vouchers_period ON vouchers(period_id);
CREATE INDEX IF NOT EXISTS idx_entries_voucher ON entries(voucher_id);
CREATE INDEX IF NOT EXISTS idx_entries_account ON entries(account_code);

-- === 默认数据: 示例公司 ===
INSERT OR IGNORE INTO companies (id, name, industry, taxpayer_type)
VALUES ('demo', '示例公司', '信息技术', 'small_scale');
