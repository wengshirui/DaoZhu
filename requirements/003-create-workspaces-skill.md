# REQ-003: create-workspaces 技能规范

> Intake ID: 2025-05-25-create-workspaces-skill

---

## 原始需求（Verbatim）

create-workspaces 要默认工作区职责（workspaces/xxx/）每个工作区是一个完全独立的 FastAPI 应用：
- 独立 Python venv
- 独立 SQLite 数据库
- 独立前端页面
- 独立端口（7801、7802…）
- 通过 workspace.json 声明元信息

优先从 github/gitee 上搜索开源高 star 项目去解决用户需求，同时改造成符合默认技术方案。
如果没有，再根据用户需求自己写。写的时候也要参考主项目 README.md。

---

## 提取意图

create-workspaces 是管家的核心技能，负责为用户建造新工作区。它的工作流程分两条路径：

1. **搜索优先**：先在 GitHub/Gitee 搜索高 star 开源项目，找到匹配用户需求的项目后，改造为符合岛主规范的独立工作区
2. **自主建造**：如果搜索无果，管家根据用户需求从零生成代码，参考主项目 README.md 的架构规范

最终产出必须是一个完全独立的 FastAPI 工作区，包含完整的目录结构。

---

## 开放问题

| # | 模块 | 问题 | AI 猜测 | 答案 |
|---|------|------|---------|------|
| 1 | 用户与现状 | 用户描述需求的方式有哪些？是纯自然语言，还是也支持模板选择？ | 主要是自然语言，如"帮我建一个记账工作区" | |
| 2 | 范围与影响 | "改造开源项目"的边界在哪里？是完整 fork 还是只提取核心逻辑？ | 提取核心逻辑，重写为 FastAPI + SQLite 架构，保留原项目 credit | |
| 3 | 范围与影响 | 搜索开源项目时，"高 star"的阈值是多少？搜索结果如何呈现给用户确认？ | star ≥ 50，展示 Top 3 让用户选择，或用户确认"没有合适的，帮我从零建" | |
| 4 | 业务规则 | 工作区创建过程中如果失败（venv 创建失败、端口冲突等），如何处理？ | 回滚已创建的文件，向用户报告具体错误，建议解决方案 | |
| 5 | 业务规则 | 创建完成后工作区是否自动启动？还是需要用户手动启动？ | 创建完成后自动启动，并在书架上显示 | |
| 6 | 范围与影响 | 工作区的 venv 依赖安装策略是什么？是否有统一的基础依赖集？ | 基础依赖：fastapi + uvicorn + aiosqlite，其余按需添加 | |

---

## 工作区产出规范（已确定）

```
workspaces/xxx/
├── app.py                  # FastAPI 入口（≤ 100 行）
├── models.py               # 数据模型（或 models/ 目录）
├── routes/                 # 路由拆分
│   ├── __init__.py
│   └── xxx.py
├── services/               # 业务逻辑
│   └── xxx.py
├── frontend/
│   ├── index.html
│   ├── css/
│   └── js/
├── .venv/                  # 独立虚拟环境
├── data.db                 # 独立 SQLite
├── schema.sql              # 数据库表设计（DDL）
├── requirements.txt        # 依赖清单
├── workspace.json          # 元信息声明
└── README.md               # 工作区说明文档
```

### workspace.json 规范

```json
{
  "id": "unique-id",
  "name": "显示名称",
  "icon": "emoji",
  "color": "#HEX",
  "version": "1.0.0",
  "description": "一句话描述",
  "port": 7801,
  "entry": "app.py",
  "python": ".venv",
  "tags": ["标签1", "标签2"],
  "source": "https://github.com/xxx/yyy 或 self-built"
}
```

### README.md 规范

每个工作区必须包含 README.md，内容结构如下：

```markdown
# {工作区名称} {icon}

> 一句话描述

---

## 介绍

2-3 段文字说明这个工作区做什么、解决什么问题、适合谁用。

## 目标

- 目标 1：核心功能描述
- 目标 2：次要功能描述
- 目标 3：...

## 功能列表

- [ ] 功能 A
- [ ] 功能 B
- [ ] 功能 C

## 注意事项

- 数据存储在本地 data.db，请勿手动修改
- 端口 {port}，如冲突请在 workspace.json 中修改
- 其他使用限制或已知问题

## 技术信息

| 项目 | 值 |
|------|-----|
| 端口 | {port} |
| 数据库 | data.db (SQLite) |
| 来源 | self-built / github.com/xxx |
| 版本 | 1.0.0 |
```

### schema.sql 规范

每个工作区必须包含 schema.sql，记录完整的数据库表设计：

```sql
-- schema.sql — {工作区名称} 数据库设计
-- 创建时间: YYYY-MM-DD
-- 说明: 此文件定义工作区的完整数据库结构

-- === 表: {table_name} ===
-- 用途: {表的业务用途}
CREATE TABLE {table_name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- 业务字段
    title TEXT NOT NULL,
    content TEXT,
    status TEXT DEFAULT 'active',
    -- 审计字段（必须）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- === 索引 ===
CREATE INDEX idx_{table}_status ON {table_name}(status);
CREATE INDEX idx_{table}_created ON {table_name}(created_at);
```

**schema.sql 规则：**
- 每张表必须有 `id`、`created_at`、`updated_at` 三个字段
- 每张表上方必须有注释说明用途
- 常用查询字段必须建索引
- 使用 SQLite 兼容的数据类型（TEXT, INTEGER, REAL, BLOB, DATETIME）
- 工作区首次启动时自动执行 schema.sql 初始化数据库

---

## 技能工作流程（已确认）

```
用户: "帮我建一个 XXX 工作区"
         │
         ▼
┌─────────────────────┐
│ 1. 理解用户需求      │
│    提取关键词/功能点  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 2. 搜索开源项目      │
│    GitHub + Gitee    │
│    展示 Top 5       │
│    以匹配度优先      │
└─────────┬───────────┘
          │
     有匹配？
    /        \
   是          否
   │           │
   ▼           ▼
┌────────┐  ┌────────────┐
│3a.展示  │  │3b.从零建造  │
│Top 5   │  │参考README  │
│让用户选 │  │生成全套代码 │
└───┬────┘  └─────┬──────┘
    │              │
    ▼              │
┌────────────────┐ │
│4. clone → 适配  │ │
│ 保留 git 历史   │ │
│ 加 workspace.json│
│ 适配前端为纯HTML │
└───┬────────────┘ │
    │              │
    └──────┬───────┘
           │
           ▼
┌─────────────────────┐
│ 5. 创建工作区目录    │
│    记录步骤进度      │
│    创建venv+安装依赖 │
│    初始化data.db     │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 6. 判断 mode        │
│    轻量→挂载主进程   │
│    标准→独立启动     │
│    注册到书架        │
└─────────────────────┘
```

### 改造方案（已确认：方案 B）

**clone → 适配 → 保留 git 历史**

1. `git clone --depth=1` 到 `workspaces/xxx/`
2. 添加 `workspace.json`、`schema.sql`、`db.py`
3. 适配前端为纯 HTML/CSS/JS（无 Node 依赖）
4. 创建 `.venv` + 安装依赖
5. 初始化 `data.db`
6. 启动 + 注册到书架

**优势**：保留 git 历史，上游更新可 merge；README 标注来源，符合开源协议。

---

## 状态

- [x] 需求录入
- [ ] 开放问题确认
- [ ] 需求提炼（含验收标准）
- [ ] 移交开发
