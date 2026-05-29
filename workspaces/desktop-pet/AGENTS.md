# 桌面宠物工作区 — 开发指南

> 给 AI 编码助手的上下文文件。修改本工作区代码时请遵循以下规则。

---

## 项目概述

这是岛主（DaoZhu）平台的"桌面宠物"工作区，让用户从 Petdex 开源社区领养像素宠物，在本地养宠物、互动。

## 架构原则

1. **商店只做展示和下载** — 不自建宠物资源，全部来自 Petdex manifest API
2. **本地优先** — 下载后的宠物完全离线可用，不依赖远程服务
3. **代理解决 CORS** — 远程 spritesheet 通过 `/api/proxy/spritesheet` 代理加载
4. **纯前端无框架** — HTML + CSS + 原生 JS，不引入 React/Vue/Node

## 关键文件

| 文件 | 职责 | 修改频率 |
|------|------|---------|
| `app.py` | FastAPI 入口 + 代理路由 | 低 |
| `routes/store.py` | 商店逻辑（manifest/下载） | 中 |
| `routes/pets.py` | 宠物 CRUD + 状态衰减 | 中 |
| `routes/interact.py` | 互动逻辑 | 低 |
| `frontend/js/app.js` | 前端主逻辑 | 高 |
| `frontend/js/renderer.js` | Spritesheet 动画渲染器 | 中 |
| `frontend/css/pet.css` | 样式 | 高 |

## 数据流

```
Petdex API (petdex.crafter.run/api/manifest)
    ↓ POST /api/store/refresh
本地缓存 (pets/_manifest.json)
    ↓ GET /api/store/manifest
前端商店页（卡片网格 + Canvas 动画预览）
    ↓ POST /api/store/download?slug=xxx
本地文件 (pets/<slug>/spritesheet.webp + pet.json)
    ↓ GET /api/pets/
前端我的宠物页（管理 + 互动）
```

## Spritesheet 渲染规则

- 格式：8 行 × 9 列，每帧 192×208px
- 渲染：Canvas 2D，`imageSmoothingEnabled = false`（保持像素锐利）
- 帧率：商店预览 6fps，互动页 8fps
- 缩放：商店卡片 0.5x，我的宠物缩略图 0.33x，互动页 2x
- 远程 URL 必须走代理：`/api/proxy/spritesheet?url=<encoded_url>`

## 前端开发注意事项

### 缓存问题
- HTML 中 JS/CSS 引用带版本号 `?v=N`，每次修改前端必须递增
- 浏览器可能缓存旧 JS，测试时用 Ctrl+Shift+R 强制刷新

### 样式规范
- 使用 CSS 变量（定义在 `:root`）
- 暗色主题，暖色调
- 卡片圆角 16px，按钮圆角 6-10px
- 动画用 CSS transition/animation，不用 JS 动画库

### 商店页逻辑
- 进入页面自动检测 manifest 是否为空，为空则自动刷新
- 刷新时显示 loading 状态
- 每页 24 个宠物，支持分页和 kind 筛选
- 每张卡片用 Canvas 播放 spritesheet 第 0 行（idle）动画

### 代理路由
- 允许的 URL 前缀：
  - `https://assets.codex-pet.org/`
  - `https://pub-94495283df974cfea5e98d6a9e3fa462.r2.dev/`
- 缓存 7 天（`Cache-Control: public, max-age=604800`）

## 测试

```bash
# 启动服务
cd workspaces/desktop-pet
python app.py

# 验证 API
curl http://localhost:7805/api/store/manifest
curl -X POST http://localhost:7805/api/store/refresh
curl http://localhost:7805/api/pets/

# 浏览器测试
# 打开 http://localhost:7805，检查：
# 1. 商店页是否自动加载宠物列表
# 2. 卡片是否有动画预览
# 3. 领养按钮是否能下载宠物
# 4. 我的宠物页是否显示已下载宠物
```

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 商店空白 | manifest 未缓存 | 页面会自动刷新，等待网络请求完成 |
| 卡片无动画 | CORS 阻止 | 确保走 `/api/proxy/spritesheet` 代理 |
| 前端改了没生效 | 浏览器缓存 | 递增 `?v=N` 版本号 |
| 下载失败 | 网络/代理问题 | 检查 httpx 是否走了系统代理 |
| `__pycache__` 导致旧代码 | Python 字节码缓存 | 删除 `__pycache__/` 并用 `-B` 启动 |

## 不要做的事

- ❌ 不要自建宠物资源库（用 Petdex）
- ❌ 不要在前端直接请求远程 spritesheet（CORS）
- ❌ 不要引入 Node.js 或前端框架
- ❌ 不要把 `pets/` 目录下的大文件提交到 git
- ❌ 不要硬编码宠物列表（从 manifest API 动态获取）
