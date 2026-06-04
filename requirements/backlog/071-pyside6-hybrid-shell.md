# 071 — 客户端壳重构：Tauri 2 替代 PySide6

> 状态: 🆕 待开发
> 优先级: P1
> T-shirt Size: L
> 录入日期: 2026-06-04
> 更新日期: 2026-06-04

---

## 问题陈述

当前岛主客户端壳使用 PySide6 + QWebEngineView，存在以下严重工程问题：

1. **打包体积不可接受** — 单文件 exe 280MB / onedir 750MB+，核心原因是 WebEngineView 自带完整 Chromium
2. **启动慢** — onefile 模式需解压到临时目录（5-10 秒白屏），onedir 模式 WebEngine 初始化也要 2-3 秒
3. **PyInstaller 路径地狱** — `sys._MEIPASS` 临时目录 vs `sys.executable` 目录，`PLATFORM_ROOT` 每次打包都出错
4. **打包产物无法直接使用** — 没有 README、没有压缩包、用户不知道怎么运行
5. **跨平台能力弱** — PySide6 + WebEngine 在 macOS/Linux 上打包同样困难
6. **图标/UI 适配坑多** — Qt SVG 不支持 emoji text、FramelessWindowHint 行为不一致

## 用户故事

**As a** 岛主用户
**I want** 下载一个小巧的压缩包，解压后双击即可运行（无需安装、无需配置）
**So that** 我在任何 Windows/macOS/Linux 电脑上都能秒启动岛主，体验如原生桌面应用

## 技术决策：为什么用 Tauri 2 替代 PySide6

### 已排除：继续 PySide6 + WebEngineView

- 打包体积 200-280MB（自带 Chromium），无法从根本缩小
- PyInstaller 路径问题反复出现（`_MEIPASS` / frozen 模式），每次改动都踩坑
- WebEngine 初始化慢，启动体验差
- 图标渲染依赖 Qt SVG（不支持 emoji），需要额外生成 .ico
- 已实测验证：两轮打包均失败（307 超时 / 标题栏丢失 / 宠物不显示）

### 已排除：pywebview

- 不支持透明窗口（宠物需要）
- 无内置系统托盘（需额外库）
- 与 PySide6 事件循环冲突（无法共存于同一进程）

### 已排除：Wails (Go)

- 透明窗口支持不成熟
- 多窗口管理弱（宠物需要独立窗口）
- 社区规模小（7k star vs Tauri 90k star）

### 选定：Tauri 2.x (Rust)

| 维度 | PySide6 (现状) | Tauri 2 (目标) |
|------|----------------|----------------|
| 壳体积 | 200-280 MB | 3-8 MB |
| 启动速度 | 2-5 秒 | <0.5 秒 |
| WebView | 自带 Chromium | 系统 WebView2/WebKit |
| 系统托盘 | 手动实现 | 内置 plugin |
| 全局快捷键 | 需 Win32 API | 内置 plugin |
| 原生通知 | 需额外库 | 内置 plugin |
| 透明窗口 | 支持 | 支持 |
| 自动更新 | 无 | 内置 plugin |
| 跨平台打包 | 困难 | 一条命令 (`tauri build`) |
| 路径问题 | 严重 | 无（`tauri::path` API） |

---

## 范围

### In Scope

**P0 — 最小可用壳**
- Tauri 2 主窗口，WebView 加载 `http://localhost:7788`
- Rust 侧管理 Python 后端子进程（启动 uvicorn、健康检查、优雅退出）
- 系统托盘图标 + 右键菜单（显示/隐藏/退出）
- 关闭窗口 → 最小化到托盘（不退出）
- 自定义标题栏（品牌 + 最小化/最大化/关闭）或沿用系统标题栏
- 启动等待页（后端未就绪时显示 loading，就绪后自动跳转）
- 窗口居中显示

**P1 — 桌面融合**
- 全局快捷键（Ctrl+D 呼出/隐藏）
- 窗口置顶切换
- 原生系统通知（AI 回复完成时）
- 窗口位置/大小记忆

**P2 — 宠物窗口**
- 独立透明 WebView 窗口渲染桌面宠物
- 宠物 HTML 页面：CSS 精灵动画 + JS 拖拽/甩出物理
- 复用已有 spritesheet 资源和动画参数
- 点击宠物 → IPC 通知主窗口前置
- 托盘菜单集成宠物控制

**P3 — 打包与分发**
- `tauri build` 生成各平台安装包
- Windows: `.msi` 安装包 或 portable `.zip`
- macOS: `.dmg`
- Linux: `.AppImage` / `.deb`
- 压缩包内含 README（告知用户如何使用）
- GitHub Release 自动构建（CI/CD）

### Out of Scope

- 修改现有前端代码（HTML/CSS/JS 保持不变）
- 修改 Python 后端（FastAPI/uvicorn 不动）
- 自动更新功能（Tauri 内置，但属于后续迭代）
- 将 Web 交互迁移到原生 Widget

---

## 架构设计

```
┌──────────────────────────────────────────────┐
│  Tauri 壳 (Rust, ~5MB)                       │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ 主窗口 (WebView)                       │  │
│  │  → loading.html (等待后端)             │  │
│  │  → http://localhost:7788 (后端就绪后)   │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ 宠物窗口 (WebView, transparent, P2)    │  │
│  │  → pet.html (CSS sprite + JS physics)  │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Rust 职责:                                  │
│  ├─ 子进程管理: 启动/监控/停止 uvicorn       │
│  ├─ 系统托盘: tray-icon plugin              │
│  ├─ 全局快捷键: global-shortcut plugin      │
│  ├─ 原生通知: notification plugin           │
│  ├─ 窗口管理: 位置记忆、置顶、多窗口        │
│  └─ IPC: 前端 ↔ Rust ↔ 宠物窗口            │
└──────────────────────────────────────────────┘

子进程: python -m uvicorn daozhu.app:app --port 7788
```

### 目录结构（新增）

```
DaoZhu/
├── src-tauri/           # Tauri 壳源码（Rust）
│   ├── Cargo.toml
│   ├── tauri.conf.json  # 窗口/打包配置
│   ├── src/
│   │   ├── main.rs      # 入口
│   │   ├── tray.rs      # 系统托盘
│   │   ├── process.rs   # Python 子进程管理
│   │   └── commands.rs  # IPC 命令
│   └── icons/           # 各平台图标
├── src-tauri-pet/       # 宠物 HTML/CSS/JS（P2）
│   ├── pet.html
│   ├── pet.css
│   └── pet.js
├── daozhu/              # Python 后端（不动）
├── workspaces/          # 工作区数据（不动）
└── ...
```

### Python 后端子进程管理

```rust
// Rust 伪代码
fn start_backend(port: u16) -> Child {
    Command::new("python")
        .args(["-m", "uvicorn", "daozhu.app:app",
               "--host", "127.0.0.1",
               "--port", &port.to_string()])
        .spawn()
}

// 健康检查：轮询直到 HTTP 响应（任何 status < 500）
// 就绪后通知 WebView 跳转到 localhost:7788
```

### 启动流程

```
用户双击 → Tauri 窗口显示 loading.html（品牌 + 加载动画）
         → Rust 启动 Python 子进程
         → Rust 轮询 localhost:7788 健康检查
         → 就绪后 WebView 导航到 localhost:7788
         → 用户看到岛主主界面（<1 秒体感）
```

---

## 验收标准

### P0 — 最小可用壳

1. **AC1**: 双击可执行文件后，<1 秒内显示带品牌 logo 的加载页面（非白屏）
2. **AC2**: Python 后端自动启动，就绪后主窗口自动显示岛主主界面
3. **AC3**: 现有前端功能全部正常：聊天（SSE 流式）、侧边栏切换、工作区打开、主题切换
4. **AC4**: 系统托盘图标显示"岛主 DaoZhu"，右键菜单含：显示主窗口 / 退出
5. **AC5**: 点击窗口关闭按钮 → 最小化到托盘（不退出），托盘"退出"才真正退出
6. **AC6**: 退出时优雅关闭 Python 后端子进程（无残留进程）
7. **AC7**: 首次启动窗口居中

### P1 — 桌面融合

8. **AC8**: Ctrl+Shift+D 全局快捷键呼出/隐藏主窗口（窗口不在前台也能响应）
9. **AC9**: 托盘菜单或快捷键可切换窗口 Always on Top
10. **AC10**: AI 回复完成时，若窗口非前台，弹出系统原生通知
11. **AC11**: 关闭时记忆窗口位置和大小，下次启动恢复

### P2 — 宠物窗口

12. **AC12**: 桌面宠物在独立透明窗口中渲染（CSS 精灵动画），视觉效果与当前 PySide6 版一致
13. **AC13**: 宠物可拖拽、甩出（带物理惯性），与当前实现行为一致
14. **AC14**: 点击宠物 → 主窗口前置并聚焦
15. **AC15**: 托盘菜单合并宠物控制：显示/隐藏宠物、切换宠物

### P3 — 打包与分发

16. **AC16**: Windows 产物为 `.zip` 压缩包（portable 免安装），解压后目录结构：
    ```
    岛主DaoZhu/
    ├── 岛主DaoZhu.exe      （<10MB）
    ├── python/              （嵌入式 Python + 依赖）
    ├── workspaces/          （示例工作区，首次运行生成）
    ├── README.txt           （使用说明）
    └── ...
    ```
17. **AC17**: README.txt 内容包含：
    - 双击 exe 即可运行（无需安装）
    - 首次运行会要求配置 API Key
    - 系统要求（Windows 10+、Edge WebView2 Runtime）
    - 常见问题（端口冲突、防火墙）
18. **AC18**: 压缩包总体积 < 50MB（不含 Python 环境）或 < 100MB（含嵌入式 Python）
19. **AC19**: macOS 产物为 `.dmg`，Linux 产物为 `.AppImage`（跨平台可构建）
20. **AC20**: 构建脚本一条命令完成：`npm run tauri build`（或等效）

---

## 打包策略

### Python 后端的分发方式

**问题**：Tauri 壳虽然小，但 Python 后端 + 依赖（FastAPI、httpx、playwright 等）仍需要分发。

**方案选择：**

| 方案 | 体积 | 用户体验 | 复杂度 |
|------|------|---------|--------|
| A. 嵌入式 Python (embeddable) | ~80MB | 解压即用，零配置 | 中 |
| B. 要求用户装 Python + pip | 0 | 需安装步骤，有门槛 | 低 |
| C. PyInstaller 打包后端 | ~50MB | exe 调用 exe | 中 |

**选定方案 A（嵌入式 Python）**：
- 使用 Python embeddable package（Windows ~15MB）
- 预装好所有依赖到 `python/Lib/site-packages/`
- Tauri 壳启动 `./python/python.exe -m uvicorn ...`
- 用户解压即用，零安装门槛

### Windows 最终产物结构

```
岛主DaoZhu-v1.0.0-win-x64.zip
└── 岛主DaoZhu/
    ├── 岛主DaoZhu.exe          (Tauri 壳, ~8MB)
    ├── python/                  (嵌入式 Python, ~80MB)
    │   ├── python.exe
    │   ├── python311._pth
    │   └── Lib/site-packages/   (FastAPI, uvicorn, etc.)
    ├── daozhu/                  (Python 源码)
    │   ├── app.py
    │   ├── frontend/            (HTML/CSS/JS)
    │   └── ...
    ├── workspaces/              (工作区目录)
    ├── config.json              (首次运行生成)
    ├── README.txt               (使用说明)
    └── LICENSE
```

### README.txt 模板

```
═══════════════════════════════════════
  🏝️  岛主 DaoZhu — 你的 AI 数字小岛
═══════════════════════════════════════

【使用方法】
  双击 "岛主DaoZhu.exe" 即可运行。

【首次运行】
  会弹出引导页面，请输入 DeepSeek API Key。
  (获取地址: https://platform.deepseek.com)

【系统要求】
  - Windows 10 (1803+) 或 Windows 11
  - 已安装 Microsoft Edge WebView2 Runtime
    (Windows 10/11 通常已预装，如未安装请访问:
     https://developer.microsoft.com/edge/webview2)

【快捷操作】
  - 关闭窗口 → 最小化到系统托盘（右下角）
  - 双击托盘图标 → 重新打开窗口
  - 右键托盘图标 → 显示菜单 / 退出
  - Ctrl+Shift+D → 全局呼出/隐藏窗口

【常见问题】
  Q: 启动后白屏？
  A: 等待 3-5 秒，后端服务正在启动。

  Q: 提示端口占用？
  A: 修改 config.json 中的 "port" 值。

  Q: 找不到托盘图标？
  A: 点击任务栏右下角的 "^" 展开隐藏图标。

【版本】v1.0.0
【开源】https://gitee.com/daozhu
```

---

## 迁移计划

### 废弃的代码

- `daozhu/shell.py` — PySide6 壳（被 Tauri 替代）
- `daozhu/pet_widget.py` — PySide6 宠物（被 pet.html 替代）
- `daozhu_main.py` — PyInstaller 入口（被 Tauri main.rs 替代）
- `岛主DaoZhu.spec` — PyInstaller 配置（废弃）
- `scripts/gen_icon.py` — 图标生成（改用 Tauri icon 工具链）

### 保留不变

- `daozhu/app.py` — FastAPI 后端
- `daozhu/frontend/` — 前端 HTML/CSS/JS
- `daozhu/config.py` — 配置管理（移除 frozen 模式判断，恢复简单路径逻辑）
- `workspaces/` — 工作区数据
- `launcher.py` — 开发模式启动器（保留供开发用）

### 分步交付建议

| 阶段 | 内容 | 产出 | 预估 |
|------|------|------|------|
| Phase 1 | P0 核心壳 + P3 打包 | 可用的 .zip 发布包 | 3-5 天 |
| Phase 2 | P1 桌面融合 | 快捷键/通知/记忆 | 2 天 |
| Phase 3 | P2 宠物窗口 | 透明窗口 + CSS 动画 | 3 天 |

---

## 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| WebView2 未预装（部分 Windows 10 LTSC） | 用户无法运行 | README 提供下载链接；启动时检测并提示 |
| 嵌入式 Python 缺少依赖 | 后端启动失败 | 构建脚本确保 `pip install` 完整 |
| macOS WebKit 与 Chrome 行为差异 | 前端样式/JS 不兼容 | 前端代码用标准 API，避免 Chrome-only 特性 |
| Rust 编译环境搭建 | 开发门槛 | 提供 Docker 构建方案；CI 自动构建 |
| 宠物 CSS 动画性能 | 低配机器掉帧 | 提供关闭宠物选项；CSS will-change 优化 |

---

## T-Shirt Size

**L** — 涉及新语言 (Rust/Tauri) 引入、子进程管理、多窗口架构、跨平台打包脚本、嵌入式 Python 环境制作。
但核心逻辑简单（壳只做窗口管理 + 进程管理），前端/后端完全不动。
建议按 Phase 1 → 2 → 3 分批交付。

## 依赖

- Tauri 2.x CLI (`npm install -g @tauri-apps/cli`)
- Rust toolchain (`rustup`)
- Python embeddable package (构建时下载)
- 现有前端代码（不改动）
- 现有 Python 后端（不改动）

## 参考

- [Tauri 2.0 文档](https://v2.tauri.app/)
- [Tauri 透明窗口](https://v2.tauri.app/reference/config/#transparent)
- [Tauri 系统托盘](https://v2.tauri.app/plugin/system-tray/)
- [Tauri 子进程管理 (shell plugin)](https://v2.tauri.app/plugin/shell/)
- [Python embeddable package](https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip)
