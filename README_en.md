# DaoZhu 🏝️

[中文](./README.md) | **English**

> Your AI-powered digital island — a personal digital sovereignty platform that truly belongs to you.

---

## 🔑 Why DaoZhu?

| Other Products | DaoZhu |
|---------------|--------|
| Require sign-up and login | **No login needed** — double-click the exe and go |
| Your data lives on their servers | **Your data stays yours** — SQLite local storage, zero cloud |
| Client apps can be shut down anytime | **Your client is yours** — open source, packaged as exe |
| AI conversations go through third parties | **Your model can be yours too** — connect Ollama for local inference |

**In one sentence: your machine is your server, your data never leaves your hands.**

---

## ✨ Core Features

- 🏝️ **Three-panel workspace** — Resources + AI chat + History
- 🤖 **AI Island Manager** — 10 tools to start/stop workspaces, manage data, generate code
- 📋 **Ready out of the box** — Ships with Todo, Accounting, and Forum workspaces
- 🧠 **Three-layer memory** — Session memory + User profile + Knowledge base (learns as you use it)
- 🏗️ **Build with one sentence** — Tell the AI what app you want, it builds it for you
- 📖 **Skill system** — Extensible skill files, AI capabilities keep evolving
- 🔒 **Fully local** — All data on your machine, works offline
- 📦 **Double-click to run** — Packaged as exe via PyInstaller, no Python needed
- 🎮 **Pixel manager** — Pure CSS pixel-art animated character with personality

---

## 🛡️ Data Sovereignty Loop

```
┌─────────────────────────────────────────────┐
│            Your Digital Island                │
│                                               │
│  📁 Your data         → Local SQLite files    │
│  🖥️ Your client       → Open source + exe     │
│  🧠 Your model        → Ollama local LLM      │
│  📱 Your remote       → Gitee Issue control   │
│                                               │
│  No sign-up. No login. No subscription.       │                           │
└─────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Option 1: Run the exe (recommended for regular users)

1. Download `daozhu.zip` from [Releases](https://gitee.com/yumen2278/DaoZhu/releases)
2. Extract to any directory
3. Double-click `daozhu.exe`
4. Browser opens automatically, follow the setup guide

### Option 2: Developer setup

```bash
git clone https://gitee.com/yumen2278/DaoZhu.git
cd DaoZhu

# Create virtual environment
uv venv .venv --python 3.11
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
uv pip install -e .

# Start the platform
python daozhu_main.py
```

Browser opens `http://localhost:7788` automatically. First launch shows the setup guide.

### Option 3: Build your own exe

```bash
uv pip install -e ".[dev]"
python build_exe.py
# Output: dist/daozhu/daozhu.exe
```

---

## 🎮 How It Works

```
You:     Build me a reading notes workspace
Manager: Building...
         ✅ "Reading Notes" created, port 7804.

You:     Add a todo: meeting tomorrow afternoon
Manager: ✅ Added to "Personal Todo".

You:     Start the accounting assistant
Manager: ✅ Accounting Assistant started, port 7803.
```

---

## 🏗️ Architecture

```
DaoZhu/
├── daozhu/                 # Platform core
│   ├── app.py              # FastAPI main service (port 7788)
│   ├── agent.py            # AI Agent (conversation loop + tool calls)
│   ├── workspace_manager.py# Workspace process management
│   ├── config.py           # Global configuration
│   ├── memory_db.py        # Memory system
│   ├── chat_service.py     # LLM streaming calls
│   ├── skill_loader.py     # Skill discovery and loading
│   ├── template_engine.py  # Template rendering engine
│   ├── tools/              # Agent tools (10)
│   └── frontend/           # Main UI
│
├── workspaces/             # Workspace directory (each runs independently)
├── templates/              # Workspace templates
├── skills/                 # Skill files
├── requirements/           # Requirement docs
├── daozhu_main.py          # Entry point
└── pyproject.toml          # Project config
```

---

## 🔧 Agent Tools

| Tool | Purpose |
|------|---------|
| `list_workspaces` | List all workspaces and their status |
| `start_workspace` | Start a workspace |
| `stop_workspace` | Stop a workspace |
| `get_workspace_info` | Get workspace details |
| `call_workspace_api` | Call workspace API (add todo, record expense, etc.) |
| `list_templates` | List available templates |
| `create_from_template` | Create workspace from template |
| `write_file` | Write file in workspace |
| `read_file` | Read workspace file |
| `list_files` | List workspace files |

---

## 📚 Default Workspaces

| Workspace | Port | Features |
|-----------|------|----------|
| 📋 Personal Todo | 7801 | Task management, subtasks, tags, priorities, daily focus |
| 💰 Accounting | 7803 | Multi-company ledgers, chart of accounts, journal entries |
| 🏝️ Forum | 7802 | Integrated with Gitee Issues, browse/post/reply |

---

## 🌈 Future Workspaces You Could Build

DaoZhu's core philosophy is **build with one sentence** — whatever you imagine, the AI helps you create it. Here's some inspiration:

| Workspace | One-liner | Possibilities |
|-----------|-----------|---------------|
| 🎬 AutoMovie Studio | AI writes script → generates storyboard → renders video | Input a story outline, output a short film |
| 💬 Private Chat Server | Locally hosted instant messaging | Family group chat, small team collaboration — no third party |
| 📚 Personal Wiki | Markdown knowledge base + full-text search | Your own Notion, but data stays local |
| 🏥 Health Tracker | Weight / sleep / exercise / diet logging | AI analyzes trends and gives suggestions |
| 🏠 Smart Home Console | Connect to Home Assistant / MQTT | "Turn off the living room lights" |
| 📝 Code Snippet Manager | Organized by language / tags | Never dig through Stack Overflow history again |
| 🎵 Local Music Library | Scan local music + player + lyrics | No streaming platform dependency |
| 📷 Photo Timeline | Local album + EXIF parsing + AI tagging | Auto-organize by location / people / time |
| 📰 RSS Reader | Feed management + AI summaries | Information without algorithmic feeds |
| 🎮 Game Save Manager | Multi-platform save backup + sync | Never lose progress when switching machines |
| 🐍 Python Learning Island | Interactive tutorials + live execution + AI tutor | Learn by doing, AI as your teacher |
| 💼 Freelancer Dashboard | Projects / clients / income / invoices | Gigs, bookkeeping, invoicing — all in one |

**Your island, your rules.** Just tell the Island Manager what you want, and it builds from scratch.

---

## ⚙️ Configuration

### AI Backend (required, choose one)

**Cloud model (DeepSeek):**
```
DEEPSEEK_API_KEY=sk-xxxxxxxx
```

**Local model (Ollama, fully offline):**
```
Install Ollama → Pull a model → Select "Local Model" in settings
```

### Gitee Token (remote control + forum, optional)

```
GITEE_TOKEN=xxxxxxxx
```

---

## 🗺️ Roadmap

### ✅ Phase 0 — Foundation (Complete)

- [x] FastAPI service + three-panel UI
- [x] Workspace process management
- [x] Global config + user onboarding
- [x] Default workspaces (Todo / Accounting / Forum)

### ✅ Phase 1 — AI Capabilities (Complete)

- [x] AI Agent conversation loop + 10 tools
- [x] SSE streaming + interrupt support
- [x] Three-layer memory + Skill tracking
- [x] Workspace templates + code generation
- [x] Agent operates workspace data

### 🚧 Phase 2 — Data Sovereignty (In Progress)

- [ ] Gitee remote control (control your island from your phone)
- [ ] Local Ollama model integration (fully offline)
- [ ] Workspace marketplace (Gitee ecosystem)
- [ ] AutoMovie intelligent theater

### 📋 Phase 3 — Release & Ecosystem

- [x] PyInstaller packaging
- [ ] Windows installer + system tray
- [ ] Gamification (sprites / achievements / levels)

---

## 🌍 World View

| Role | What | Does |
|------|------|------|
| 🏝️ Island | Your local space | Hosts everything |
| 🧠 Brain (LLM) | AI model | Thinks (cloud or local) |
| 🏛️ Manager (Agent) | AI executor | Receives commands, coordinates building |
| 📖 Skill | Knowledge & process | Manager's experience |
| 🔧 Tool | Operational ability | Start/stop workspaces, read/write files |
| 🏠 Building (Workspace) | Independent app | Each functional module on the island |

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11+ / FastAPI |
| Frontend | Pure HTML + CSS + JS (no Node dependency) |
| AI Model | DeepSeek / OpenAI / Ollama / compatible APIs |
| Database | SQLite (platform-level + per-workspace) |
| Isolation | subprocess + independent ports |
| Packaging | PyInstaller |
| Package Manager | uv + pyproject.toml |

---

## Who Is This For?

| You are... | DaoZhu helps you... |
|-----------|---------------------|
| Regular user | Own your own toolset without knowing tech |
| Small business owner | Accounting, project management, CRM — one platform |
| Developer | Rapid prototyping, local toolchain, custom workspaces |
| Privacy-conscious | All data local, model can be local too |
| Remote worker | Use Gitee Issues as a remote control from any device |

---

## Philosophy

> Your machine is your server. Your bookshelf is your internet portal.
> AI is your architect, workspaces are rooms you build, the whole platform is your own town.
>
> No login. No subscription. No data leaks.
> This is not a productivity tool — it's a new form of personal digital sovereignty.

---

## License

MIT

## Community

- QQ Group: 1102100710
- GitHub: https://github.com/wengshirui/DaoZhu
- Gitee: https://gitee.com/yumen2278/DaoZhu
