# 🐾 桌面宠物工作区

> 养一只像素宠物，陪你写代码、陪你逛小岛。

---

## 定位

从 [Petdex](https://petdex.crafter.run/)（2700+ 开源 Codex 宠物）中挑选宠物，下载到本地，在岛主界面和电脑桌面上养宠物、互动。

## 核心功能

| 功能 | 说明 |
|------|------|
| 宠物商店 | 对接 Petdex manifest API，浏览/搜索/筛选 2700+ 宠物 |
| 一键领养 | 点击下载 spritesheet 到本地，离线可用 |
| 宠物管理 | 选择活跃宠物、删除、查看状态 |
| 状态系统 | 饥饿/口渴/心情/精力，随时间衰减 |
| 互动 | 喂食/喂水/抚摸/玩耍，影响状态和动画 |
| 动画播放 | Canvas 渲染 spritesheet（8行×9列，192×208px/帧） |

## 技术栈

- 后端：FastAPI + SQLite + httpx
- 前端：纯 HTML/CSS/JS（无框架）
- 数据源：Petdex manifest API（`petdex.crafter.run/api/manifest`）
- 资源格式：Codex Pet 标准（`pet.json` + `spritesheet.webp`）

## 目录结构

```
workspaces/desktop-pet/
├── app.py                  # FastAPI 入口（端口 7805）
├── db.py                   # SQLite 工具
├── schema.sql              # 数据库 DDL
├── workspace.json          # 工作区配置
├── requirements.txt        # Python 依赖
├── routes/
│   ├── store.py            # 商店 API（manifest/下载/搜索）
│   ├── pets.py             # 宠物 CRUD + 状态
│   └── interact.py         # 互动 API
├── pets/                   # 已下载的宠物资源（gitignore）
│   └── <slug>/
│       ├── pet.json
│       └── spritesheet.webp
└── frontend/
    ├── index.html
    ├── css/pet.css
    └── js/
        ├── api.js          # API 封装
        ├── renderer.js     # Spritesheet 动画渲染器
        └── app.js          # 主逻辑
```

## 启动

```bash
cd workspaces/desktop-pet
python app.py
# 浏览器打开 http://localhost:7805
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/store/manifest` | 获取宠物目录（分页+筛选） |
| POST | `/api/store/refresh` | 从 Petdex 刷新 manifest |
| POST | `/api/store/download?slug=xxx` | 下载宠物到本地 |
| GET | `/api/store/search?q=xxx` | 搜索宠物 |
| GET | `/api/pets/` | 列出本地宠物 |
| GET | `/api/pets/active` | 获取活跃宠物 |
| POST | `/api/pets/{id}/activate` | 设置活跃宠物 |
| DELETE | `/api/pets/{id}` | 删除宠物 |
| POST | `/api/interact/` | 执行互动 |
| GET | `/api/proxy/spritesheet?url=xxx` | 代理远程图片 |

## Spritesheet 格式

```
8 行 × 9 列 = 72 帧
每帧 192 × 208 像素
总尺寸 1728 × 1664 像素（或 1536 × 1872，取决于具体宠物）

行对应动画状态：
Row 0: idle（待机）
Row 1: wave（打招呼）
Row 2: run（奔跑）
Row 3: failed（失败/饥饿）
Row 4: review（审视/口渴）
Row 5: jump（跳跃/开心）
Row 6: extra1（吃东西）
Row 7: extra2（喝水）
```

## 已知问题

- spritesheet 通过后端代理加载，首次加载较慢（2-3MB/张）
- 需要网络才能刷新商店目录和下载新宠物
- 已下载的宠物完全离线可用

## 后续计划

- [ ] Phase 2：PySide6 桌面透明窗口（宠物跑到桌面上）
- [ ] 宠物穿梭到岛主主界面
- [ ] 装扮系统（帽子/围巾/眼镜）
- [ ] 与岛主 Agent 状态联动（Agent 工作时宠物也忙碌）
