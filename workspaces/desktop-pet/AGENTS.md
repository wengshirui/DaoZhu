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

## Spritesheet 渲染规则（对齐 Petdex 标准）

### 格式规格

- **网格**：8 列 × 9 行（注意：列是帧，行是状态）
- **单帧**：192 × 208 px
- **总尺寸**：1536 × 1872 px（`8×192=1536`，`9×208=1872`）
- **格式**：WebP（透明背景）

### 9 种动画状态（来自 Petdex `pet-states.ts`）

| 行 | 状态 ID | 帧数 | 时长(ms) | 用途 | 岛主适配 |
|----|---------|------|----------|------|---------|
| 0 | idle | 6 | 1100 | 待机呼吸 | 正常状态 |
| 1 | running-right | 8 | 1060 | 向右跑 | 开心/刚互动 |
| 2 | running-left | 8 | 1060 | 向左跑 | 移动中 |
| 3 | waving | 4 | 700 | 打招呼 | 用户打开时 |
| 4 | jumping | 5 | 840 | 跳跃 | 非常开心 |
| 5 | failed | 8 | 1220 | 失败/难过 | 饥饿 |
| 6 | waiting | 6 | 1010 | 等待 | 口渴 |
| 7 | running | 6 | 820 | 原地跑 | 玩耍中 |
| 8 | review | 6 | 1030 | 审视/思考 | 无聊 |

**关键：每行帧数不同！** 不能统一用 8 或 9 帧循环。

### 渲染方案（复用 Petdex 方案）

**方案 A：纯 CSS（商店卡片预览）— 推荐**

Petdex 的核心技巧：用 CSS `steps()` 动画驱动 `background-position`，零 JS 开销。

```css
.pet-sprite-frame {
    --pet-scale: 1;
    width: calc(192px * var(--pet-scale));
    height: calc(208px * var(--pet-scale));
    overflow: hidden;
    contain: layout paint;
}

.pet-sprite {
    --sprite-row: 0;
    --sprite-frames: 6;
    --sprite-duration: 1100ms;
    --sprite-y: calc(var(--sprite-row) * -208px);
    --sprite-end-x: calc(var(--sprite-frames) * -192px);
    width: 192px;
    height: 208px;
    background-image: var(--sprite-url);
    background-repeat: no-repeat;
    background-size: 1536px 1872px;
    image-rendering: pixelated;
    transform: scale(var(--pet-scale)) translateZ(0);
    transform-origin: top left;
    will-change: background-position;
    animation: pet-state var(--sprite-duration) steps(var(--sprite-frames)) infinite;
}

@keyframes pet-state {
    from { background-position: 0 var(--sprite-y); }
    to { background-position: var(--sprite-end-x) var(--sprite-y); }
}
```

使用时通过 CSS 变量控制状态：
```html
<div class="pet-sprite-frame" style="--pet-scale: 0.5">
    <div class="pet-sprite" style="
        --sprite-url: url('spritesheet.webp');
        --sprite-row: 0;
        --sprite-frames: 6;
        --sprite-duration: 1100ms;
    "></div>
</div>
```

**方案 B：Canvas（互动页，需要动态切换状态）**

- `imageSmoothingEnabled = false`（保持像素锐利）
- 帧率根据状态时长计算：`fps = frames * 1000 / durationMs`
- 缩放：互动页 2x

### 性能优化（来自 Petdex）

- `content-visibility: auto` — 离屏卡片暂停动画
- `contain: layout paint` — 隔离重绘范围
- `transform: translateZ(0)` — GPU 合成层，避免 WebP 反复解码
- `will-change: background-position` — 提示浏览器优化

### 远程 URL 代理

- 远程 spritesheet 必须走代理：`/api/proxy/spritesheet?url=<encoded_url>`
- **但 CSS background-image 不受 CORS 限制**，商店预览可直接用 CDN URL
- Canvas 加载需要 `crossOrigin = 'anonymous'`，必须走代理

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

## 代理路由
- 允许的 URL 前缀：
  - `https://assets.codex-pet.org/`
  - `https://pub-94495283df974cfea5e98d6a9e3fa462.r2.dev/`
  - `https://yu2vz9gndp.ufs.sh/`（UploadThing，部分宠物存这里）
- 缓存 7 天（`Cache-Control: public, max-age=604800`）
- **注意**：CSS background-image 不受 CORS 限制，商店卡片预览可直接用 CDN URL，无需代理

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
- ❌ 不要在前端直接请求远程 spritesheet（CORS）— **但 CSS background-image 例外，可直接用 CDN URL**
- ❌ 不要引入 Node.js 或前端框架
- ❌ 不要把 `pets/` 目录下的大文件提交到 git
- ❌ 不要硬编码宠物列表（从 manifest API 动态获取）
- ❌ 不要给所有状态用统一帧数（每行帧数不同，见状态表）
- ❌ 不要用 `background-size: 1728px 1664px`（正确值是 `1536px 1872px`）

---

## Petdex 复用参考

> 本工作区的宠物资源和渲染方案直接对接 Petdex 生态。以下是从 Petdex 源码
> （`d:\python\petdex`）中提取的可复用知识，避免重复造轮子。

### Manifest API 响应格式

```
GET https://petdex.crafter.run/api/manifest
响应：{
  generatedAt: "ISO时间",
  total: 2702,
  pets: [{
    slug: "boba",
    displayName: "Boba",
    kind: "creature" | "character" | "object",
    submittedBy: "railly",
    spritesheetUrl: "https://pub-...r2.dev/.../spritesheet.webp",
    petJsonUrl: "https://pub-...r2.dev/.../pet.json",
    zipUrl: "https://pub-...r2.dev/.../boba.zip"
  }, ...]
}
```

- 缓存策略：`max-age=60, s-maxage=300, stale-while-revalidate=3600`
- 本地缓存到 `pets/_manifest.json`，避免频繁请求

### Petdex CSS 动画方案（核心复用）

Petdex 的 `src/app/globals.css` 中定义了完整的 sprite 动画系统，
**不依赖任何 JS 框架**，纯 CSS 变量 + keyframes：

**关键 class 对照：**

| Petdex class | 用途 | 我们的对应 |
|---|---|---|
| `.pet-sprite-frame` | 裁剪容器 | `.sprite-frame` |
| `.pet-sprite` | 动画元素 | `.sprite-anim` |
| `.pet-sprite-static` | 静态首帧 | 新增（列表缩略图用） |
| `.pet-sprite-stage` | 背景光晕 | `.card-preview` |

**Petdex 的性能技巧（直接复用）：**
1. `content-visibility: auto` + `contain-intrinsic-size` — 离屏暂停
2. `contain: layout paint` — 隔离重绘
3. `transform: translateZ(0)` — GPU 合成，防 WebP 反复解码
4. `will-change: background-position` — 动画优化
5. `@media (prefers-reduced-motion: reduce)` — 无障碍：禁用动画

**Petdex 的卡片背景光晕（可选复用）：**
```css
.pet-sprite-stage {
    background: radial-gradient(
        circle at 50% 38%,
        rgb(64 64 70 / 0.85) 0%,
        rgb(40 40 48 / 0.55) 55%,
        transparent 80%
    );
}
```

### Petdex 状态定义（权威来源）

来自 `petdex/src/lib/pet-states.ts`，这是 Codex Pet 生态的标准：

```javascript
const PET_STATES = [
    { id: "idle",          row: 0, frames: 6, durationMs: 1100 },
    { id: "running-right", row: 1, frames: 8, durationMs: 1060 },
    { id: "running-left",  row: 2, frames: 8, durationMs: 1060 },
    { id: "waving",        row: 3, frames: 4, durationMs: 700  },
    { id: "jumping",       row: 4, frames: 5, durationMs: 840  },
    { id: "failed",        row: 5, frames: 8, durationMs: 1220 },
    { id: "waiting",       row: 6, frames: 6, durationMs: 1010 },
    { id: "running",       row: 7, frames: 6, durationMs: 820  },
    { id: "review",        row: 8, frames: 6, durationMs: 1030 },
];
```

### 宠物类型筛选

Manifest 中每只宠物有 `kind` 字段，三种值：
- `creature` — 生物（猫、狗、龙等）
- `character` — 角色（动漫人物、名人等）
- `object` — 物品（台灯、回形针等）

直接用这个字段做筛选 Tab，不需要自己打标签。

### 下载策略

优先用 `zipUrl` 下载完整包（含 pet.json + spritesheet.webp），
比分别下载两个文件更可靠。zip 解压到 `pets/<slug>/` 目录。

### 参考文件路径（在 petdex 仓库中）

| 文件 | 复用价值 |
|------|---------|
| `src/lib/pet-states.ts` | 状态定义（帧数/时长/行号） |
| `src/app/globals.css` 第 390-560 行 | CSS sprite 动画系统 |
| `src/components/pet-sprite.tsx` | CSS 变量驱动逻辑 |
| `src/components/static-pet-sprite.tsx` | 静态首帧方案 |
| `src/components/pet-floater.tsx` | 浮动宠物交互（拖拽/状态循环） |
| `src/app/api/manifest/route.ts` | API 响应格式 |
| `src/lib/types.ts` | 数据类型定义 |
