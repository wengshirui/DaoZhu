# DaoZhu 🏝️ — Your AI Desktop Assistant

**English** | [中文](./README.md)

An open-source, standalone desktop app. Tell it what you need in plain language — it builds tools and automates tasks for you.

---

## What it does

### 1. Build tools

Want a simple app — reading notes, expense tracker, idea collector, file organizer?
Just tell it. It generates the tool for you. No coding required.

### 2. Save time

Things you do every day or every week — check websites for updates, organize files, generate reports.
Describe the steps once. It runs them automatically on schedule.

### 3. Desktop pet

Adopt a pixel pet that lives on your desktop. Drag it, toss it, double-click to open the main window.

---

## How is it different

- No signup, no login. Open and use.
- Data stays on your computer. Nobody else can see it.
- Open source. Anyone can inspect or modify the code.
- Works fully offline with a local AI model.

---

## Examples

```
"Build me a reading notes tool — record book name, thoughts, and rating."

"Every morning at 9, check these websites for updates and notify me."

"Organize these messy files by month and type."
```

You talk, it does. Not happy? Tell it to change. Iterate until it's right.

---

## Who is it for

Anyone who wants to save time or build things on their computer.
No technical background needed. Just know what you want.

---

## Quick Start

### Download & Run (Recommended)

1. Download latest zip from [Releases](https://gitee.com/yumen2278/DaoZhu/releases)
2. Extract anywhere
3. Double-click `岛主DaoZhu.exe`
4. First run: follow setup guide to enter API Key (DeepSeek recommended)

> Requirements: Windows 10+. ~60MB download.

### Shortcuts

| Action | Effect |
|--------|--------|
| Close window | Minimizes to system tray (doesn't quit) |
| Double-click tray | Reopen window |
| Double-click exe again | Shows existing window (no duplicate) |
| Ctrl+Alt+D | Global toggle show/hide |
| Double-click desktop pet | Show main window |
| Drag pet | Move pet (it runs!) |
| Right-click tray | Menu: Show / Pin / Pet / Quit |

### Developer Setup

```bash
git clone https://gitee.com/yumen2278/DaoZhu.git
cd DaoZhu
uv venv .venv --python 3.11
.venv\Scripts\activate
uv pip install -e .
python daozhu_main.py          # 启动后端 + 浏览器（开发模式）
python daozhu_main.py --shell  # 启动后端 + Tauri 客户端壳
```

Opens browser at `http://localhost:7788` with hot-reload.

---

## AI Model Options

| Option | Description | Cost |
|--------|-------------|------|
| DeepSeek | Cloud, recommended | ~$0.001/conversation |
| Ollama | Local, fully offline | Free |
| OpenAI | Cloud, GPT series | Pay per use |

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Client Shell | Tauri 2 (Rust) — system WebView |
| Desktop Pet | Tauri transparent window + CSS sprite |
| Backend | Python 3.11+ / FastAPI |
| Frontend | Pure HTML + CSS + JS |
| Database | SQLite |
| AI | DeepSeek / OpenAI / Ollama |

---

## Contributing

Issues, PRs, and ideas are all welcome.

- Gitee: https://gitee.com/yumen2278/DaoZhu
- GitHub: https://github.com/wengshirui/DaoZhu

---

## License

MIT
