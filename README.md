# 岛主 DaoZhu 🏝️

> 让每个人都能搭建属于自己的数字世界。

岛主是一个运行在本地的 AI 工作台平台。你拥有一座"数字岛屿"，在上面建造任何你需要的应用——记账、聊天、项目管理、知识库……你说了算。

**不需要懂编程，不需要懂 AI。** 告诉管家你想要什么，管家帮你建造。

---

## 世界观

| 角色 | 是什么 | 做什么 |
|------|--------|--------|
| 🏝️ 岛 | 你的本地空间 | 承载一切，数据和应用都在这里 |
| 🧠 大脑（LLM） | AI 模型 | 负责思考和理解 |
| 🤵 管家（Agent） | AI 执行者 | 接收指令，协调建造 |
| 📖 技能（Skill） | 知识和流程 | 管家做事的经验 |
| 🔧 工具（MCP） | 外部连接器 | 连接浏览器、文件、API |
| 🏠 建筑（工作区） | 独立应用 | 岛上的每一个功能模块 |

行业提供了大脑、管家、技能、工具。**岛主给普通人一个"家"来安放这一切。**

---

## 核心体验

```
你：帮我建一个记账的工作区
管家：好的，正在建造「个人记账」... ✅ 已添加到书架。

你：帮我建一个番茄钟
管家：好的，正在建造「番茄钟」... ✅ 支持 25+5 循环，已上架。
```

打开浏览器，书架上多了两本"书"——点击即用。

---

## 功能概览

- **📚 书架管理** — 主界面是书架，每个工作区是一本书，点击打开，右键管理
- **🤖 AI 建造** — 描述需求，管家从零生成完整工作区（后端+前端+数据库）
- **📦 市场安装** — 从 Gitee 工作区市场一键安装现成模板
- **🔒 数据本地** — 所有数据在你电脑上，无云端依赖
- **🧩 隔离互通** — 工作区独立运行，但可通过管家协作

---

## 架构

```
DaoZhu/
├── daozhu/                 # 平台核心
│   ├── app.py              # FastAPI 主服务（端口 7788）
│   ├── agent.py            # 平台级 AI Agent（工作区生成/管理）
│   ├── workspace_manager.py# 工作区注册、启停、进程管理、端口分配
│   ├── config.py           # 全局配置
│   └── frontend/           # 书架 UI（纯 HTML/CSS/JS）
│
├── workspaces/             # 工作区根目录
│   ├── finance/            # 财务工作区（AccoBot 迁移而来）
│   │   ├── .venv/
│   │   ├── app.py
│   │   ├── data.db
│   │   ├── frontend/
│   │   └── workspace.json
│   ├── chat/               # 聊天工作区
│   └── ...                 # 用户创建的其他工作区
│
├── templates/              # 内置工作区模板（AI 生成时参考）
├── config.json             # 全局配置文件
├── pyproject.toml
└── README.md
```

### 平台层职责（daozhu/）

| 模块 | 职责 |
|------|------|
| `app.py` | 主 FastAPI 服务，书架 API + 静态文件 |
| `agent.py` | 平台 Agent：理解用户意图，生成/管理工作区 |
| `workspace_manager.py` | 进程生命周期：启动、停止、健康检查、端口分配 |
| `config.py` | 全局配置：AI API Key、工作区目录、端口范围 |
| `frontend/` | 书架 UI：展示工作区列表、AI 对话窗口 |

### 工作区职责（workspaces/xxx/）

每个工作区是一个**完全独立的 FastAPI 应用**：
- 独立 Python venv
- 独立 SQLite 数据库
- 独立前端页面
- 独立端口（7801、7802…）
- 通过 `workspace.json` 声明元信息

---

## workspace.json 规范

```json
{
  "id": "finance",
  "name": "财务助手",
  "icon": "💰",
  "color": "#2563EB",
  "version": "1.0.0",
  "description": "AI 驱动的记账、报表、报税",
  "port": 7801,
  "entry": "app.py",
  "python": ".venv",
  "tags": ["财务", "记账"],
  "source": "https://gitee.com/yumen2278/accobot"
}
```

---

## 技术选型

| 层级 | 选型 |
|------|------|
| 平台后端 | Python 3.11+ / FastAPI |
| 平台前端 | 纯 HTML + CSS + JS（无 Node 依赖） |
| AI 模型 | DeepSeek / OpenAI / 兼容接口 |
| 工具协议 | MCP（Model Context Protocol） |
| 工作区隔离 | venv + subprocess |
| 数据库 | SQLite（每工作区独立） |
| 打包 | PyInstaller → 单 exe |
| 包管理 | uv + pyproject.toml |

---

## 与 AccoBot 的关系

AccoBot（财务助手）是岛主平台的**第一个工作区**。

| | AccoBot（之前） | 岛主（现在） |
|--|----------------|-------------|
| 定位 | 财务垂直工具 | 通用工作台平台 |
| 边界 | 只做财务 | 承载任何应用 |
| AI 角色 | 会计专家 | 通用建筑师 |
| 架构 | 单体应用 | 平台 + 工作区 |

AccoBot 的所有功能保留，作为 `workspaces/finance/` 继续运行。平台层不侵入工作区代码。

---

## 工作区来源

### 🤖 AI 生成

```
你：帮我建一个读书笔记工作区，能记录书名、摘抄、感想，按标签分类
管家：正在建造...
     - app.py（FastAPI + CRUD 路由）
     - frontend/index.html（卡片列表 + 标签筛选）
     - data.db（SQLite schema）
     - workspace.json
     ✅ 建造完成，已上架。
```

### 📦 从市场安装

```
你：从市场安装一个项目管理工作区
管家：找到 3 个相关模板：
     1. 看板式项目管理（⭐ 128）
     2. 甘特图项目管理（⭐ 56）
     3. 极简 TODO（⭐ 203）
     安装哪个？
```

### 📂 导入本地目录

选择一个符合 workspace.json 规范的本地文件夹，直接注册到书架。

---

## 路线图

### Phase 0 — MVP（当前）

- [ ] 平台 FastAPI 主服务
- [ ] 书架 UI（展示工作区列表、状态指示）
- [ ] 工作区进程管理（启动/停止/健康检查）
- [ ] AccoBot 适配为独立工作区
- [ ] 浏览器新标签打开工作区

### Phase 1 — AI 建造

- [ ] 平台级 Agent（理解需求、生成代码）
- [ ] AI 对话窗口（书架底部）
- [ ] 工作区代码生成（app.py + frontend + schema）
- [ ] 自动创建 venv 并安装依赖

### Phase 2 — 生态

- [ ] Gitee 工作区市场（搜索 + 一键安装）
- [ ] 工作区模板规范
- [ ] 工作区间通信协议

### Phase 3 — 发布

- [ ] PyInstaller 打包
- [ ] Windows 安装向导
- [ ] 系统托盘 + 开机自启

---

## 快速开始（开发者）

```bash
git clone https://gitee.com/yumen2278/DaoZhu.git
cd DaoZhu

uv venv .venv --python 3.11
.venv\Scripts\activate
uv pip install -e .

# 启动平台
daozhu serve
```

浏览器打开 `http://localhost:7788`，看到你的书架。

---

## 适合谁

| 你是谁 | 岛主怎么帮你 |
|--------|-------------|
| 普通人 | 不懂技术也能拥有自己的工具集 |
| 小老板 | 记账、项目管理、客户跟进，一个平台搞定 |
| 开发者 | 快速原型、本地工具链、自定义工作区 |
| 注重隐私的人 | 所有数据本地，零云端依赖 |

---

## 理念

> 互联网诞生之初，每个人都可以拥有自己的主页。后来平台崛起，大多数人的"网络存在"变成了别人产品里的一个账号。
>
> 岛主想把这件事反过来。
>
> 你的机器是你的服务器，你的书架是你的互联网入口。AI 是你的建筑师，工作区是你盖的房间，整个平台是你自己的城镇。
>
> 这不是一个效率工具，是一种新的个人数字主权。

---

## License

MIT

## 交流

- QQ群：1102100710
- GitHub：https://github.com/wengshirui/DaoZhu
- Gitee：https://gitee.com/yumen2278/DaoZhu
