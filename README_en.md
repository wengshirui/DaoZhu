# DaoZhu 🏝️ — Your AI Digital Island

**English** | [中文](./README.md)

> A truly personal digital sovereignty platform — your machine is your server, your data stays with you.

---

## 🔑 Why DaoZhu?

| Others | DaoZhu |
|--------|--------|
| Requires signup / login | **No login** — double-click exe and go |
| Data on their servers | **Your data** — SQLite local storage, zero cloud |
| App can be shut down anytime | **Your client** — open source + standalone exe |
| AI goes through third parties | **Your model** — Ollama local inference |

**In one line: your machine is your server, your data is forever yours.**

---

## ✨ What it can do

- 🤖 **AI Butler** — manage everything in natural language (DeepSeek / Ollama / OpenAI)
- 🏗️ **Build with one sentence** — "Build me a reading notes workspace" → AI generates a complete app
- 📋 **Workspaces** — Todo, accounting, forum, desktop pet… each runs independently
- 🐾 **Desktop Pet** — adopt pixel pets from Petdex community, drag & bounce on your desktop
- 🎬 **Stickman Theater** — one sentence generates animated shorts, AI writes the script
- 🧠 **Learns about you** — three-layer memory system, AI remembers your preferences
- 🌐 **Web access** — ask about weather, news, tech questions — AI searches for you
- 📁 **Bind folders** — turn any local folder into a workspace shortcut
- 💰 **Cost efficient** — DeepSeek prefix cache (90% input savings) + auto session compression
- 🔒 **Safe** — dangerous operations auto-blocked, permission rules configurable

---

## 🚀 Quick Start

### Option 1: Download & Run (Recommended)

1. Download latest zip from [Releases](https://gitee.com/yumen2278/DaoZhu/releases)
2. Extract anywhere
3. Double-click `岛主DaoZhu.exe`
4. First run auto-installs environment; follow browser setup guide
5. Subsequent launches auto-update

> Comes with Git + uv bundled. Nothing else to install.

### Option 2: Developer Setup

```bash
git clone https://gitee.com/yumen2278/DaoZhu.git
cd DaoZhu
uv venv .venv --python 3.11
.venv\Scripts\activate
uv pip install -e .
python daozhu_main.py
```

Browser opens `http://localhost:7788` automatically.

---

## 🎮 Usage Examples

```
You: Build me a reading notes workspace
Butler: Building... ✅ "Reading Notes" created

You: What's the weather today?
Butler: 🌤️ Sunny in Hangzhou, 28°C

You: Add a todo: meeting tomorrow afternoon
Butler: ✅ Added to "Personal Todo"

You: Bind D:\Projects\my-app as a workspace
Butler: ✅ Bound "my-app" — click to open folder
```

---

## 📚 Built-in Workspaces

| Workspace | Description |
|-----------|-------------|
| 📋 Personal Todo | Tasks, subtasks, tags, daily focus |
| 💰 Finance Assistant | Bookkeeping, vouchers, balance queries |
| 🏝️ Forum | Gitee Issues integration, community |
| 🐾 Desktop Pet | Petdex store + pet management + desktop companion |
| 🎬 Stickman Theater | AI screenplay → Canvas animation |

Tell the butler to build more: knowledge base, RSS reader, health tracker…

---

## ⚙️ Configuration

### AI Model (pick one)

| Option | Description | Cost |
|--------|-------------|------|
| DeepSeek | Cloud, best quality | ~$0.001/conversation |
| Ollama | Local, fully offline | Free |
| OpenAI | Cloud, GPT series | Pay per use |

### Gitee Token (optional)

Enables the forum workspace + remote control features.

---

## 🏗️ Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11+ / FastAPI |
| Frontend | Pure HTML + CSS + JS (no Node) |
| AI | DeepSeek / OpenAI / Ollama / compatible APIs |
| Database | SQLite |
| Distribution | PyInstaller launcher + bundled Git/uv |

---

## 🤝 Contributors

| Contributor | Role |
|-------------|------|
| [@wengshirui](https://gitee.com/yumen2278) | Creator & Lead Developer |
| [@yanpeng](https://gitee.com/yanpeng) | Contributor |

Contributions welcome! Issues, PRs, and ideas are all appreciated.

---

## 📄 License

MIT

---

## 💬 Community

- QQ Group: 1102100710
- GitHub: https://github.com/wengshirui/DaoZhu
- Gitee: https://gitee.com/yumen2278/DaoZhu
