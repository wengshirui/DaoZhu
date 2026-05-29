# 052 — 桌面宠物工作区

> 状态: 🚧 Phase 1 已完成骨架，待修复 bug
> 优先级: P0
> T-shirt Size: L — 新工作区 + 桌面应用（PySide6）+ 开源资源集成 + 跨界面穿梭机制
> 录入日期: 2026-05-29

---

## 问题陈述

用户希望岛主有一个"桌面宠物"功能，参考 codex-pet 生态，能从开源社区选择像素宠物，在岛主界面和电脑桌面上养宠物、互动，增加使用趣味性和情感连接。

## 范围

**In Scope:**
- 新建"桌面宠物"工作区
- 从 codex-pet.org / petdex 等开源社区浏览/下载宠物资源
- 宠物管理：选择、切换、删除已下载宠物
- 宠物互动：喂食、喂水、打扮、状态系统（饥饿、口渴、心情）
- 宠物穿梭：在工作区内 → 岛主主界面 → 电脑桌面三个层级活动
- 兼容 Codex Pet 资源格式（8×9 spritesheet + pet.json）

**Out of Scope:**
- 宠物联网对战/社交
- 宠物商城（付费购买）
- 移动端适配

---

## User Story

> As a 岛主用户，I want 在我的数字小岛上养一只桌面宠物，它能在工作区、主界面和电脑桌面上自由活动，so that 我的数字空间更有温度和陪伴感。

---

## 验收标准

1. 工作区内有"宠物商店"页面，可浏览开源社区的宠物列表（含预览动画）
2. 用户可一键下载宠物资源到本地，兼容 Codex Pet 格式
3. "我的宠物"页面展示已下载宠物，可选择当前活跃宠物
4. 宠物有基础状态系统：饥饿值、口渴值、心情值，随时间衰减
5. 用户可执行互动操作：喂食（+饥饿）、喂水（+口渴）、打扮（换装/配饰）
6. 状态影响宠物动画表现（开心时活泼、饥饿时萎靡）
7. Phase 1：宠物可在岛主 Web 界面内穿梭（工作区页面 ↔ 主界面），使用 CSS fixed 定位
8. Phase 2：宠物可"跑到"电脑桌面上，使用 PySide6 透明无边框窗口实现
9. 用户可设置宠物活动范围：仅本工作区 / 岛主全区域 / 电脑桌面
10. 宠物状态数据持久化到本地 SQLite

---

## Codex Pet 资源格式（调研结论）

### 文件结构

```
~/.codex/pets/<pet-name>/
├── pet.json            # 元数据（名称、描述、spritesheet 路径）
└── spritesheet.webp    # 8列 × 9行 精灵图
```

### Spritesheet 规格

| 属性 | 值 |
|------|-----|
| 尺寸 | 1536 × 1872 像素 |
| 网格 | 8 列 × 9 行 |
| 单帧 | 192 × 208 像素 |
| 格式 | WebP（透明背景） |
| 动画 | 每行一个状态，每行 8 帧循环播放 |

### 9 种动画状态（每行一个）

| 行号 | Codex 原始状态 | 岛主适配含义 |
|------|---------------|-------------|
| 0 | idle | 待机（正常状态） |
| 1 | running | 开心（刚被喂食/互动后） |
| 2 | waiting | 饥饿（饥饿值低） |
| 3 | review | 口渴（口渴值低） |
| 4 | waving | 打招呼（用户打开岛主时） |
| 5 | 自定义 | 睡觉 |
| 6 | 自定义 | 走路（穿梭移动中） |
| 7 | 自定义 | 吃东西 |
| 8 | 自定义 | 喝水 |

### pet.json 示例

```json
{
  "name": "Tater",
  "description": "A playful pixel potato companion",
  "spritesheet": "spritesheet.webp",
  "rows": 9,
  "columns": 8,
  "frameWidth": 192,
  "frameHeight": 208
}
```

### 资源来源

| 来源 | 数量 | 说明 |
|------|------|------|
| [petdex (crafter-station)](https://github.com/crafter-station/petdex) | 2400+ | 公开画廊，最大资源库 |
| [codex-pet.org](https://codex-pet.org) | 数百 | 社区分享页，支持预览/下载 |
| [codexpets.org](https://codexpets.org) | 数百 | 浏览+安装一体 |
| [awesome-codex-pet](https://github.com/legeling/awesome-codex-pet) | 精选合集 | 带预览动画的策展列表 |
| [itch.io](https://itch.io) 搜索 "codex pet" | 若干 | 独立创作者作品 |

---

## 技术方案

### Phase 1 — Web 内穿梭（纯前端）

**难度：⭐⭐ 简单**

```
渲染方式：Canvas 或 CSS background-position 动画
穿梭机制：岛主主界面用 position: fixed 叠加宠物层
工作区内：通过 postMessage 或共享 localStorage 同步宠物位置
资源存储：workspaces/desktop-pet/pets/<name>/ 目录
动画驱动：requestAnimationFrame，每 100ms 切换帧
```

**Web 端 spritesheet 播放核心逻辑：**

```javascript
// 播放第 row 行动画（8帧循环）
function animatePet(ctx, spritesheet, row, frameWidth, frameHeight) {
  let frame = 0;
  setInterval(() => {
    ctx.clearRect(0, 0, frameWidth, frameHeight);
    ctx.drawImage(
      spritesheet,
      frame * frameWidth, row * frameHeight,  // 源坐标
      frameWidth, frameHeight,                 // 源尺寸
      0, 0, frameWidth, frameHeight            // 目标
    );
    frame = (frame + 1) % 8;
  }, 120);  // ~8fps
}
```

### Phase 2 — 桌面透明窗口（PySide6）

**难度：⭐⭐⭐ 中等**

```
框架：PySide6（Qt6 Python 绑定）
窗口：QWidget + FramelessWindowHint + WA_TranslucentBackground
动画：QTimer 驱动帧切换，QPixmap 裁剪 spritesheet
交互：鼠标拖拽、右键菜单、点击触发互动
通信：HTTP API 与岛主 Web 服务同步状态
```

**PySide6 透明窗口核心逻辑：**

```python
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter

class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool  # 不在任务栏显示
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.spritesheet = QPixmap("spritesheet.webp")
        self.frame = 0
        self.row = 0  # 当前状态行
        self.frame_w = 192
        self.frame_h = 208
        self.resize(self.frame_w, self.frame_h)

        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)
        self.timer.start(120)  # ~8fps

    def next_frame(self):
        self.frame = (self.frame + 1) % 8
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(
            0, 0,
            self.spritesheet,
            self.frame * self.frame_w,
            self.row * self.frame_h,
            self.frame_w, self.frame_h
        )
```

### 状态系统

```python
# 宠物状态模型
class PetState:
    hunger: int = 100      # 0-100，每小时 -5
    thirst: int = 100      # 0-100，每小时 -8
    happiness: int = 100   # 0-100，每小时 -3

    def get_animation_row(self) -> int:
        if self.hunger < 30: return 2   # 饥饿动画
        if self.thirst < 30: return 3   # 口渴动画
        if self.happiness > 80: return 1  # 开心动画
        return 0  # 待机
```

### 共享架构（与 055 待办侧边栏）

桌面宠物和待办侧边栏都需要 PySide6 桌面进程，合并为**岛主桌面伴侣**：

```
岛主桌面伴侣（单进程）
├── 系统托盘图标（右键菜单：显示宠物/侧边栏/设置/退出）
├── 宠物透明窗口（本需求）
├── 侧边栏窗口（055 需求）
└── HTTP Client ←→ 岛主 Web 服务 :7788
```

---

## 参考项目

| 项目 | 技术栈 | 参考价值 |
|------|--------|---------|
| [DyberPet](https://github.com/ChaozhongLiu/DyberPet) | PySide6 | 桌面宠物框架，最接近我们需要的 Python 方案 |
| [codex-pets-react](https://github.com/backnotprop/codex-pets-react) | React | Web 端 spritesheet 渲染组件 |
| [petdex](https://github.com/crafter-station/petdex) | Next.js | 公开宠物画廊 API，2400+ 资源 |
| [WindowPet](https://github.com/SeakMengs/WindowPet) | Tauri + React | 跨平台桌面宠物（Rust 方案参考） |
| [desktop-pet (wkostusiak)](https://github.com/wkostusiak/desktop-pet) | Python/tkinter | 最简桌面宠物实现 |
| [pyCatAI-pet](https://github.com/R37r0-Gh057/pyCatAI-pet) | Python | AI 驱动的桌面宠物 |

---

## 工作区目录结构

```
workspaces/desktop-pet/
├── app.py                  # FastAPI 入口
├── workspace.json          # 工作区配置
├── requirements.txt        # PySide6 等依赖
├── data.db                 # 宠物状态持久化
├── schema.sql              # DDL
├── routes/
│   ├── __init__.py
│   ├── store.py            # 宠物商店 API（浏览/下载）
│   ├── pets.py             # 我的宠物 CRUD
│   └── interact.py         # 互动 API（喂食/喂水/打扮）
├── services/
│   ├── __init__.py
│   ├── pet_manager.py      # 宠物状态管理
│   ├── store_service.py    # 资源下载/缓存
│   └── animation.py        # 动画状态映射
├── desktop/
│   ├── __init__.py
│   ├── pet_window.py       # PySide6 透明窗口（Phase 2）
│   ├── tray.py             # 系统托盘
│   └── main.py             # 桌面伴侣入口
├── pets/                   # 已下载的宠物资源
│   └── <pet-name>/
│       ├── pet.json
│       └── spritesheet.webp
└── frontend/
    ├── index.html          # 工作区主页
    ├── css/
    │   └── pet.css
    └── js/
        ├── app.js          # 主入口
        ├── api.js          # API 封装
        ├── store.js        # 宠物商店页面
        ├── my-pets.js      # 我的宠物页面
        ├── interact.js     # 互动界面
        └── renderer.js     # spritesheet 动画渲染器
```

---

## 数据库设计

```sql
-- 已下载的宠物
CREATE TABLE pets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT,
    description TEXT,
    source_url TEXT,
    local_path TEXT NOT NULL,
    is_active INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 宠物状态
CREATE TABLE pet_state (
    pet_id INTEGER PRIMARY KEY REFERENCES pets(id),
    hunger INTEGER DEFAULT 100,
    thirst INTEGER DEFAULT 100,
    happiness INTEGER DEFAULT 100,
    last_fed_at DATETIME,
    last_watered_at DATETIME,
    last_interact_at DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 互动记录
CREATE TABLE interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER REFERENCES pets(id),
    action TEXT NOT NULL,  -- feed / water / pet / dress
    value_change INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 装扮/配饰
CREATE TABLE accessories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER REFERENCES pets(id),
    type TEXT NOT NULL,    -- hat / scarf / glasses
    asset_path TEXT,
    is_equipped INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 开发计划

| 阶段 | 内容 | 预估 | 状态 |
|------|------|------|------|
| Step 1 | 工作区骨架 + 后端 API（商店/宠物/互动） | 1 天 | ✅ 完成 |
| Step 2 | 前端 HTML/CSS/JS + spritesheet 渲染器 | 1 天 | ✅ 完成 |
| Step 3 | 对接 codex-pet.org 真实数据 + 后端代理 | 0.5 天 | ✅ 完成 |
| Step 4 | 前端 bug 修复 + 视觉打磨 | 0.5 天 | 🚧 待做 |
| Step 5 | 宠物下载 + 本地管理完善 | 0.5 天 | 待做 |
| Step 6 | 岛主主界面宠物叠加层（Phase 1 穿梭） | 1 天 | 待做 |
| Step 7 | PySide6 桌面透明窗口（Phase 2） | 2 天 | 待做 |
| Step 8 | 系统托盘 + 桌面伴侣整合 | 1 天 | 待做 |

**已完成：Step 1-3（约 2.5 天）**
**剩余：Step 4-8（约 5 天）**

### 已完成内容（2026-05-29）

**后端（完整可用）：**
- `app.py` — FastAPI 入口，端口 7805，含 spritesheet 代理
- `db.py` — SQLite 连接工具
- `schema.sql` — 4 张表（pets/pet_state/interactions/settings）
- `routes/store.py` — 商店 API（目录/标签/搜索/刷新/下载）
- `routes/pets.py` — 宠物 CRUD + 状态衰减计算
- `routes/interact.py` — 互动 API（喂食/喂水/抚摸/玩耍）
- `/api/proxy/spritesheet` — 代理远程 spritesheet（绕过 CORS）

**前端（基本可用，待打磨）：**
- `index.html` — 三页面结构（宠物库/我的宠物/互动）
- `css/pet.css` — Codex Pet Gallery 风格暗色主题
- `js/api.js` — API 封装层
- `js/renderer.js` — Spritesheet 动画渲染器 + 代理加载
- `js/app.js` — 主逻辑（Tab/商店/宠物管理/互动/状态条）

**数据源：**
- 内置 12 只热门宠物（含真实 assets.codex-pet.org spritesheet URL）--全部下载下来
- 支持"刷新"从 codex-pet.org 爬取更多宠物
- 标签筛选 + 搜索 + 分页

### 已知问题

- [ ] 旧进程缓存导致需要手动清理 `__pycache__` 后重启
- [ ] workspace.json 中 `start_mode` 需要与岛主平台对接
- [ ] 刷新按钮爬取逻辑需要更健壮的 HTML 解析
- [ ] 前端卡片在 spritesheet 加载慢时无 loading 状态提示

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| petdex API 不稳定/变更 | 本地缓存宠物列表 JSON，支持手动导入 |
| PySide6 在某些 Windows 版本透明窗口异常 | 降级为半透明背景，或用 tkinter 备选 |
| spritesheet.webp 格式浏览器兼容性 | 下载时转换为 PNG，或用 Canvas 解码 |
| 宠物穿梭到工作区 iframe 内有跨域限制 | 仅在岛主主界面层穿梭，工作区内通过 API 通知 |

---

## 依赖

- PySide6（Phase 2，桌面透明窗口）
- petdex / codex-pet.org（宠物资源来源）
- 岛主主界面需增加宠物叠加层（全局 JS 组件）
- Pillow（图片处理，WebP→PNG 转换）
