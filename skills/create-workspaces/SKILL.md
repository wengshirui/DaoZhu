# Create Workspaces Skill

> 岛主平台核心技能：为用户建造新工作区

---

## 描述

根据用户需求创建完整的工作区。优先搜索 GitHub/Gitee 高星开源项目作为参考，
理解其核心逻辑后用 FastAPI + SQLite + 纯 HTML/JS 改造为岛主规范的独立工作区。
如果搜索无果，从零生成全套代码。

---

## 适用场景

- 用户说"帮我建一个 XXX 工作区"
- 用户需要某类应用（待办、记账、笔记、看板等）
- 用户想把某个开源项目变成本地工作区

---

## 完整工作流程

### Phase 1: 理解需求

从用户描述中提取：
- **核心功能**：这个工作区要做什么？（如：任务管理、记账、笔记）
- **关键实体**：数据模型有哪些？（如：任务、项目、标签）
- **核心操作**：用户主要做什么？（如：增删改查、筛选、统计）
- **UI 形态**：列表？看板？表格？卡片？

### Phase 2: 搜索开源项目

**搜索策略：**
1. 用核心功能关键词搜索 GitHub（英文关键词效果更好）
2. 按 star 数排序，关注 star ≥ 50 的项目
3. 不限定技术栈 — 任何语言的项目都可以参考其需求和逻辑
4. 重点看项目的 README、功能列表、数据模型设计

**搜索示例：**
```
搜索词: "todo list app" OR "task management" self-hosted stars:>50
搜索词: "personal finance" OR "expense tracker" open source
搜索词: "note taking" OR "knowledge base" self-hosted
```

**评估标准：**
- Star 数（越高越好，说明需求验证充分）
- 功能完整度（是否覆盖用户需求）
- 架构清晰度（是否容易理解和改造）
- 活跃度（最近是否有更新）

### Phase 3: 决策 — 向用户确认

搜索完成后，向用户展示结果：

```
找到以下高星项目供参考：

1. Super Productivity (⭐ 18.8k) — Angular + Electron
   功能：任务管理、时间追踪、子任务、标签、番茄钟
   
2. Vikunja (⭐ 3k) — Go + Vue  
   功能：看板/列表/甘特图、标签、提醒、共享

3. Tasks.md (⭐ 1k) — Node + React
   功能：Markdown 存储、看板式、自托管

建议参考 #1 的核心任务管理逻辑，用 FastAPI + SQLite 重写。
需要的功能范围：[列出建议的功能子集]

确认这个方案吗？还是有调整？
```

**用户可能的回复：**
- "就按这个来" → 进入 Phase 4
- "功能太多了，只要 XXX" → 调整范围后进入 Phase 4
- "没有合适的，帮我从零建" → 跳到 Phase 4b

### Phase 4: 设计与实现

#### 4a. 参考开源项目改造

1. **提取核心逻辑**（不是 fork，是理解后重写）：
   - 数据模型设计（哪些表、哪些字段、什么关系）
   - 核心业务规则（状态流转、筛选逻辑、排序规则）
   - UI 交互模式（列表/卡片/看板的交互方式）

2. **用岛主技术栈重写**：
   - 后端：FastAPI + SQLite（同步 sqlite3）
   - 前端：纯 HTML + CSS + JS（无框架）
   - 遵循 AGENTS.md 文件规模约束（≤ 500 行/文件）

#### 4b. 从零建造

参考 README.md 架构规范，按以下顺序生成：
1. schema.sql（先设计数据模型）
2. routes/（API 路由）
3. frontend/（UI 页面）
4. app.py（入口整合）
5. workspace.json + README.md（元信息）

### Phase 5: 创建工作区文件

**必须产出的文件清单：**

```
workspaces/{id}/
├── app.py              # FastAPI 入口（≤ 100 行）
├── db.py               # 数据库连接工具（≤ 20 行）
├── schema.sql          # 完整表设计
├── routes/
│   ├── __init__.py     # 路由汇总
│   └── {domain}.py     # 按领域拆分的路由
├── frontend/
│   ├── index.html      # 页面骨架
│   ├── css/
│   │   ├── base.css    # 变量 + 重置 + 主题
│   │   └── components.css  # 组件样式
│   └── js/
│       ├── api.js      # API 封装
│       └── app.js      # 主逻辑
├── workspace.json      # 元信息
└── README.md           # 说明文档
```

**workspace.json 模板：**
```json
{
  "id": "{kebab-case-id}",
  "name": "{中文显示名}",
  "icon": "{emoji}",
  "color": "{#HEX}",
  "version": "1.0.0",
  "description": "{一句话描述}",
  "port": {下一个可用端口},
  "entry": "app.py",
  "python": ".venv",
  "tags": ["{标签1}", "{标签2}"],
  "start_mode": "manual",
  "hidden": false,
  "source": "{github URL 或 self-built}"
}
```

### Phase 6: 测试验证

1. **启动测试**：用项目主 .venv 启动工作区
   ```bash
   cd workspaces/{id}
   ../../.venv/Scripts/python.exe -m uvicorn app:app --port {port}
   ```

2. **API 测试**：验证核心 CRUD 接口
   - GET /api/{resource}/ → 返回列表
   - POST /api/{resource}/ → 创建成功
   - PUT /api/{resource}/{id} → 更新成功
   - DELETE /api/{resource}/{id} → 删除成功

3. **前端测试**：浏览器打开确认
   - 页面正常渲染
   - 数据能正常展示
   - 交互功能正常（创建、编辑、删除）

4. **平台集成测试**：从主平台启动
   - POST /api/workspaces/{id}/start → 状态变为 running
   - 主界面书架显示新工作区
   - 点击卡片能跳转到工作区页面

---

## 技术约束

| 约束 | 要求 |
|------|------|
| 后端 | FastAPI + 同步 sqlite3 |
| 前端 | 纯 HTML + CSS + JS，无框架 |
| 数据库 | SQLite，每工作区独立 data.db |
| 文件大小 | 每个文件 ≤ 500 行 |
| Python 环境 | 优先用项目主 .venv，有冲突才建独立 venv |
| 端口 | 7801-7899 范围内，不与已有工作区冲突 |
| 前端美学 | 使用 frontend-design skill 指导 UI 设计 |

---

## 前端设计要求

调用 `frontend-design` skill 的指导原则：
- 每个工作区有独特的美学方向（不要千篇一律）
- 使用霞鹜文楷字体
- 支持 CSS 变量主题
- 响应式布局
- 有意义的微交互动画

---

## schema.sql 规则

- 每张表必须有 `id`、`created_at`、`updated_at`
- 每张表上方有注释说明用途
- 常用查询字段建索引
- 使用 `IF NOT EXISTS` 防止重复创建
- 可包含默认数据的 `INSERT OR IGNORE`

---

## app.py 模板

```python
"""
{工作区名称} — 工作区入口
端口: {port}
"""

import sqlite3
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routes import router as api_router

DB_PATH = Path(__file__).parent / "data.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
FRONTEND_DIR = Path(__file__).parent / "frontend"


def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="{工作区名称}", version="1.0.0", lifespan=lifespan)
app.include_router(api_router, prefix="/api")
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")
```

---

## db.py 模板

```python
"""数据库连接工具"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

---

## ⚠️ 踩坑记录（创建工作区时必读）

| 坑 | 原因 | 正确做法 |
|----|------|----------|
| 工作区读不到平台配置 | 用相对路径找 .env | 轻挂载: `from daozhu.config_db import get_secret`；独立进程: 调平台 API |
| workspace.json 中文变乱码 | 写入时没指定 UTF-8 | 始终 `encoding="utf-8"` |
| 轻挂载 from routes import 失败 | sys.path 没保持 | 主平台已修复，不需要工作区处理 |
| Playwright 在 async 中报错 | 用了 sync_playwright | 必须用 `async_playwright` |
| 工作区需要平台配置时 | 不知道怎么获取 | 优先选 lightweight 模式，可直接 import daozhu 模块 |

### 选择 mode 的决策树

```
工作区需要读取平台配置（API Key/Token）？
  → 是 → mode: lightweight（可直接 import daozhu）
  → 否 → 表 ≤ 3 且无额外依赖？
           → 是 → mode: lightweight
           → 否 → mode: standard
```

---

## 实际案例：个人待办工作区

参考项目：Super Productivity (⭐ 18.8k, Angular + Electron)
改造范围：提取核心任务管理逻辑，去掉番茄钟/时间追踪/第三方集成
技术改造：Angular → 纯 HTML/JS，Electron → FastAPI，IndexedDB → SQLite
美学方向：工业实用 × 温暖纸质（手账本风格）

产出文件：
- app.py (50行) + db.py (15行)
- schema.sql (55行) — tasks/projects/tags 三表
- routes/tasks.py (130行) + projects.py (85行) + tags.py (65行)
- frontend/index.html (95行)
- frontend/css/base.css (115行) + components.css (250行)
- frontend/js/api.js (30行) + app.js (190行)
- workspace.json + README.md
