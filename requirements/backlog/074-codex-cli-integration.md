# 074 — Codex CLI 集成 + 代码工坊工作区

> 状态: 📋 待开发
> 优先级: P1
> T-shirt Size: L
> 录入日期: 2026-06-05
> 更新: 2026-06-05 — 新增"代码工坊"可视化管理工作区

---

## 问题陈述

当前岛主的代码相关任务由内置 Agent 直接执行，存在两个问题：

1. **能力不足** — 内置 Agent 的代码生成能力弱于 Codex CLI 这类专业 AI 编程工具
2. **不可见** — 用户不知道有哪些代码项目、哪些 Agent 在跑、历史任务结果如何，完全黑盒

解决：**Codex CLI 接管代码执行 + 一个可视化"代码工坊"工作区统一管理所有代码项目和 Agent**。

## 用户故事

**As a** 岛主用户
**I want** 所有代码任务自动通过 Codex CLI 执行，并且有一个可视化工作区管理我的代码项目和 Agent
**So that** 代码质量更高，同时我能看到每个项目状态、Agent 在干什么、历史任务结果

---

## 核心场景

```
场景 A：代码任务执行
用户说："帮我创建一个记账工作区"
  → 岛主 Agent 识别为代码任务
  → 检查 Codex CLI → 已安装 → 调用 Codex CLI 执行
  → 结果展示 + 自动注册到"代码工坊"

场景 B：代码工坊管理
用户打开"代码工坊"工作区
  → 看到所有代码项目卡片（名称、状态、最后活动时间）
  → 看到 Agent 面板（哪些 Agent 在跑、当前任务、队列）
  → 可以手动创建新项目、重跑历史任务、查看日志
```

---

## Part 1：Codex CLI 集成（后端能力）

### 范围

#### In Scope
- 🤖 代码任务路由：识别代码任务并分发到 Codex CLI
- 📦 自动安装：检测未安装时自动安装 `codex-cli` + `codex-relay`
- 🔗 自动配置：配置 deepseek-v4 为默认模型
- 🔑 API Key 复用：使用主项目 API key，不额外询问
- ✅ 安装验证 + 降级策略

#### Out of Scope
- Codex CLI 本身二次开发
- 多模型切换
- 离线模式

### 验收标准

| # | AC |
|---|-----|
| 1 | Agent 识别代码任务（创建工作区、修改代码、生成项目、重构）并路由到 Codex CLI |
| 2 | 非代码任务不走 Codex CLI，岛主 Agent 自行处理 |
| 3 | 检测 Codex CLI 是否安装（`codex --version`） |
| 4 | 未安装自动安装 + 配置 codex-relay + deepseek-v4 |
| 5 | API key 从主项目配置读取 |
| 6 | 安装后自动健康检查 |
| 7 | 失败降级回内置 Agent 并提示用户 |
| 8 | 执行结果反馈给用户 |
| 9 | 打开工作区的时候如果codex有更新就提示更新，用户选择执行 |

---

## Part 2：代码工坊工作区（前端可视化）--分为为系统类型的工作区

> 工作区 ID: `code-workshop`，类型: `system`

### 范围

#### In Scope
- 📊 **项目面板**：卡片式展示所有托管的代码项目
  - 项目名、类型（Python/JS/Rust/Tauri）、状态（活跃/空闲/报错）
  - 最后活动时间、代码行数、关联的 Agent
  - 点击进入项目详情（文件树 + 最近提交 + Codex 任务历史）
- 🤖 **Agent 面板**：可视化当前运行的 Agent
  - Agent 名称/ID、当前任务、运行时长、状态指示灯
  - 任务队列（排队中的代码任务列表）
  - 可手动终止/重试 Agent 任务
- 🚀 **任务启动器**：从工作区直接发起代码任务
  - 输入需求描述 → Codex CLI 接管执行
  - 选择目标项目（新建或选已有）
  - 实时日志流（滚动查看 Codex CLI 输出）
- 📜 **历史面板**：所有代码任务的历史记录
  - 时间线展示：任务描述 → 执行状态 → 结果摘要
  - 可点击查看完整日志
  - 支持重跑历史任务
- 🔧 **设置面板**：
  - Codex CLI 路径配置
  - Agent 并发数限制
  - 默认项目目录

#### Out of Scope
- Git 完整 GUI（不做 SourceTree）
- 在线协作
- 性能分析/Profiling

### 验收标准

| # | AC |
|---|-----|
| 9 | 存在"代码工坊"系统工作区，入口在岛主首页可见 |
| 10 | 项目面板展示所有代码项目（至少含名称、状态、最后活动时间） |
| 11 | 点击项目卡片可查看详情（文件结构 + Codex 任务历史） |
| 12 | Agent 面板展示当前运行的 Agent（名称、任务、状态灯） |
| 13 | 任务队列可见，支持手动取消排队任务 |
| 14 | 可从工作区发起新代码任务（输入描述 → 选择项目 → 执行） |
| 15 | 实时日志流：执行过程中滚动展示 Codex CLI 输出 |
| 16 | 历史面板展示所有已完成/失败任务的时间线 |
| 17 | 支持重跑历史任务（一键复现） |
| 18 | 设置面板可配置 Codex CLI 路径和并发数 |

---

## 依赖

- 主项目 API key 配置
- 网络访问（Codex CLI 安装 + API 调用）
- #068 工作区分类（system 类型，✅ 已完成）
- #070 工作区排序（✅ 已完成）

---

## 技术方向

### 后端

1. **Codex CLI Wrapper**：Python subprocess 封装
2. **任务队列**：asyncio.Queue 管理并发代码任务
3. **项目注册表**：SQLite 表 `code_projects` 记录项目元数据
4. **任务日志表**：`codex_tasks` 记录每次 Codex CLI 调用的输入/输出/状态

### 前端（代码工坊工作区）

```
code-workshop/
├── app.py           # FastAPI 路由（< 500 行）
├── static/
│   ├── index.html   # 主布局（三栏：项目 | Agent | 日志）
│   ├── css/
│   │   ├── workshop.css   # 工坊主题样式
│   │   └── components.css # 卡片/状态灯/日志窗组件
│   └── js/
│       ├── api.js         # API 调用封装
│       ├── projects.js    # 项目面板逻辑
│       ├── agents.js      # Agent 面板逻辑
│       ├── launcher.js    # 任务启动器逻辑
│       └── history.js     # 历史面板逻辑
└── services/
    ├── codex_executor.py  # Codex CLI 调用封装
    └── project_registry.py # 项目注册管理
```

### 数据模型

```sql
-- 代码项目注册表
CREATE TABLE IF NOT EXISTS code_projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    workspace_id TEXT,       -- 关联的岛主工作区（可为空）
    path TEXT NOT NULL,      -- 项目本地路径
    language TEXT,           -- python/javascript/rust
    status TEXT DEFAULT 'active',  -- active/idle/error
    last_activity_at TEXT,
    codex_task_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Codex 任务日志
CREATE TABLE IF NOT EXISTS codex_tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    agent_id TEXT,           -- Codex Agent 标识
    prompt TEXT NOT NULL,    -- 用户/系统输入
    status TEXT DEFAULT 'queued',  -- queued/running/done/failed
    output TEXT,             -- Codex CLI 输出
    error TEXT,              -- 错误信息
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL
);
```
