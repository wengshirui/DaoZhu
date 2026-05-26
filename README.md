# 岛主 DaoZhu 🏝️

> 你的AI数字小岛！。

岛主是一个运行在本地的 AI 工作台平台。你拥有一座"数字岛屿"，在上面建造任何你需要的应用——待办、记账、论坛、笔记……你说了算。

**不需要懂编程，不需要懂 AI。** 告诉岛管理员你想要什么，它帮你建造。

---

## ✨ 已实现功能

- **🏝️ 三栏工作台界面** — 左侧资源面板 + 中间 AI 对话 + 右侧历史/日志
- **🤖 AI 岛管理员** — 10 个工具，能启停工作区、操作数据、生成代码
- **📋 默认工作区** — 个人待办、财务助手、岛主论坛（对接 Gitee Issues）
- **🧠 三层记忆** — 会话记忆 + 用户画像 + 知识库（FTS5 全文搜索）
- **🏗️ 模板引擎** — 一键从模板生成新工作区
- **📖 Skill 系统** — 可扩展的技能文件，指导 AI 行为
- **⚙️ 设置页面** — 配置 DeepSeek API Key、Gitee Token、主题
- **� 像素岛管理员** — 纯 CSS 像素动画角色（思考翻书、工作搬运）
- **🔒 数据本地** — 所有数据在你电脑上，零云端依赖
- **📦 可打包** — PyInstaller 打包为 exe，双击即用

---

## 🚀 快速开始

### 方式一：开发者运行

```bash
git clone https://gitee.com/yumen2278/DaoZhu.git
cd DaoZhu

# 创建虚拟环境
uv venv .venv --python 3.11
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
uv pip install -e .

# 启动平台
python daozhu_main.py
```

浏览器自动打开 `http://localhost:7788`，首次进入引导页配置 API Key。

### 方式二：exe 直接运行（普通用户）

1. 从 [Releases](https://gitee.com/yumen2278/DaoZhu/releases) 下载 `daozhu.zip`
2. 解压到任意目录
3. 双击 `daozhu.exe`
4. 浏览器自动打开，按引导配置即可使用

### 方式三：自行打包 exe

```bash
# 安装开发依赖
uv pip install -e ".[dev]"

# 执行打包
python build_exe.py

# 输出目录
dist/daozhu/daozhu.exe
```

---

## 🎮 核心体验

```
你：帮我建一个读书笔记工作区
岛管理员：好的，正在建造...
         ✅ 「读书笔记」已创建，端口 7804。

你：添加一个待办：明天下午开会
岛管理员：✅ 已添加到「个人待办」。

你：启动财务助手
岛管理员：✅ 财务助手已启动，端口 7803。
```

---

## 🏗️ 架构

```
DaoZhu/
├── daozhu/                 # 平台核心
│   ├── app.py              # FastAPI 主服务（端口 7788）
│   ├── agent.py            # AI Agent（对话循环 + 工具调用）
│   ├── workspace_manager.py# 工作区进程管理（启停/健康检查/端口分配）
│   ├── config.py           # 全局配置（config.json + .env）
│   ├── memory_db.py        # 记忆系统（用户画像/知识库/Skill追踪）
│   ├── memory_service.py   # 记忆注入与提取
│   ├── chat_db.py          # 对话持久化
│   ├── chat_service.py     # LLM 流式调用
│   ├── skill_loader.py     # Skill 发现与加载
│   ├── template_engine.py  # 模板渲染引擎
│   ├── tools/              # Agent 工具（10个）
│   └── frontend/           # 主界面 UI
│
├── workspaces/             # 工作区目录
│   ├── todo/               # 📋 个人待办
│   ├── accobot/            # 💰 财务助手
│   └── forum/              # 🏝️ 岛主论坛
│
├── templates/              # 工作区模板
│   └── crud-basic/         # 基础增删改查模板
│
├── skills/                 # 技能文件
│   ├── create-workspaces/  # 工作区创建技能
│   └── frontend-design/    # 前端设计技能
│
├── requirements/           # 需求文档
├── daozhu_main.py          # 启动入口（推荐）
├── build_exe.py            # 打包脚本
├── pyproject.toml          # 项目配置
└── config.json             # 用户配置
```

---

## 🔧 Agent 工具清单

| 工具 | 用途 |
|------|------|
| `list_workspaces` | 列出所有工作区及状态 |
| `start_workspace` | 启动工作区 |
| `stop_workspace` | 停止工作区 |
| `get_workspace_info` | 获取工作区详情 |
| `call_workspace_api` | 调用工作区 API（添加待办/记账等） |
| `list_templates` | 列出可用模板 |
| `create_from_template` | 从模板创建工作区 |
| `write_file` | 在工作区内写文件 |
| `read_file` | 读取工作区文件 |
| `list_files` | 列出工作区文件 |

---

## 📚 默认工作区

| 工作区 | 端口 | 功能 |
|--------|------|------|
| 📋 个人待办 | 7801 | 任务管理、子任务、标签、优先级、今日聚焦 |
| 💰 财务助手 | 7803 | 多公司账套、会计科目、凭证录入、余额查询 |
| 🏝️ 岛主论坛 | 7802 | 对接 Gitee Issues，浏览/发帖/回复 |

---

## ⚙️ 配置

### API Key（必须）

在 `.env` 文件中配置：

```
DEEPSEEK_API_KEY=sk-xxxxxxxx
```

或通过引导页 / 设置页面配置。

### Gitee Token（论坛发帖用，可选）

```
GITEE_TOKEN=xxxxxxxx
```

获取方式：Gitee → 设置 → 私人令牌 → 新建

---

## 🗺️ 路线图

### ✅ Phase 0 — 基础平台（已完成）

- [x] FastAPI 主服务 + 三栏 UI
- [x] 工作区进程管理（启停/健康检查/端口分配）
- [x] 全局配置系统
- [x] 用户引导页面
- [x] 默认工作区（待办/财务/论坛）

### ✅ Phase 1 — AI 能力（已完成）

- [x] AI Agent 对话循环 + 10 个工具
- [x] SSE 流式响应 + 打断输出
- [x] 三层记忆系统 + Skill 追踪
- [x] 工作区模板 + 代码生成
- [x] Skill 加载系统
- [x] 管家操作工作区数据

### 🚧 Phase 2 — 生态（进行中）

- [ ] Gitee 工作区市场
- [ ] 游戏化（精灵/成就/等级）
- [ ] 本地性能检测 + 智能推荐

### 📋 Phase 3 — 发布

- [x] PyInstaller 打包
- [ ] Windows 安装向导
- [ ] 系统托盘 + 开机自启

---

## 🌍 世界观

| 角色 | 是什么 | 做什么 |
|------|--------|--------|
| 🏝️ 岛 | 你的本地空间 | 承载一切 |
| 🧠 大脑（LLM） | AI 模型 | 负责思考 |
| 🏛️ 岛管理员（Agent） | AI 执行者 | 接收指令，协调建造 |
| 📖 技能（Skill） | 知识和流程 | 管理员做事的经验 |
| 🔧 工具（Tool） | 操作能力 | 启停工作区、读写文件 |
| 🏠 建筑（工作区） | 独立应用 | 岛上的每一个功能模块 |

---

## 技术选型

| 层级 | 选型 |
|------|------|
| 平台后端 | Python 3.11+ / FastAPI |
| 平台前端 | 纯 HTML + CSS + JS（无 Node 依赖） |
| AI 模型 | DeepSeek / OpenAI / 兼容接口 |
| 数据库 | SQLite（平台级 + 每工作区独立） |
| 工作区隔离 | subprocess + 独立端口 |
| 打包 | PyInstaller |
| 包管理 | uv + pyproject.toml |

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

> 你的机器是你的服务器，你的书架是你的互联网入口。
> AI 是你的建筑师，工作区是你盖的房间，整个平台是你自己的城镇。
>
> 这不是一个效率工具，是一种新的个人数字主权。

---

## License

MIT

## 交流

- QQ群：1102100710
- GitHub：https://github.com/wengshirui/DaoZhu
- Gitee：https://gitee.com/yumen2278/DaoZhu
