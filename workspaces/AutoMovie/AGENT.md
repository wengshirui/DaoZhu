# 🧠 AutoMovie 开发指南（AI Agent 专用）

> 生成动画时严格遵循此文档。违反原则会导致效果变差。

---

## ⚠️ 核心铁律

1. **不要追求写实** — 火柴人 > 精细人物。越简单越好。
2. **不要用 SVG 图标当角色** — SVG 素材只用于场景装饰，角色必须用 Canvas 火柴人。
3. **不要分幕切换** — 用时间轴连续播放，角色自然进出场。
4. **不要把文字信息分散** — 旁白和对话统一在底部字幕条。
5. **不要播放太快** — 每段对话后至少留 3 秒阅读时间。
6. **场景切换时清除旧对话** — 否则场景变了对话没变很违和。

---

## 技术架构

```
┌─────────────────────────────────────────┐
│  Canvas 层（requestAnimationFrame）       │
│  ├── drawBg()     背景渐变 + 几何装饰     │
│  ├── drawDecor()  SVG 素材 (data URI)    │
│  └── drawChar()   火柴人角色              │
├─────────────────────────────────────────┤
│  DOM 层                                   │
│  ├── .emoji-pop   emoji 弹出动画          │
│  ├── .dialogue-box 对话（底部白色条）      │
│  ├── .narration   旁白（底部深色条）       │
│  └── .scene-label 场景标签                │
└─────────────────────────────────────────┘
```

---

## 时间轴格式

```javascript
const TIMELINE = [
    { t: 0,     action: 'label',    text: '📍 场景名' },
    { t: 0,     action: 'narr',     text: '旁白文字' },
    { t: 1500,  action: 'enter',    id: 'charId', x: 450, y: 280 },
    { t: 3000,  action: 'emoji',    id: 'charId', e: '😊' },
    { t: 4500,  action: 'dialogue', who: '角色名', text: '"台词"' },
    { t: 7000,  action: 'arm',      id: 'charId', arm: 'point' },
    { t: 8000,  action: 'move',     id: 'charId', x: 300 },
    { t: 10000, action: 'exit',     id: 'charId' },
    { t: 12000, action: 'end' },
];
```

### action 类型

| action | 参数 | 说明 |
|--------|------|------|
| `enter` | id, x, y | 角色入场（从屏幕外滑入） |
| `exit` | id | 角色退场（滑出屏幕） |
| `move` | id, x, y? | 角色移动到新位置 |
| `arm` | id, arm | 改变手臂姿态 |
| `emoji` | id, e | 角色头顶弹出 emoji |
| `dialogue` | who, text | 底部白色对话条 |
| `narr` | text | 底部深色旁白条 |
| `label` | text | 场景标签（同时清除旧对话） |
| `end` | — | 动画结束 |

### 手臂姿态 (arm)

| 值 | 视觉 | 适用场景 |
|----|------|---------|
| `normal` | 自然下垂 V 形 | 默认站立 |
| `up` | 双手举起 | 欢呼、惊讶、投降 |
| `hip` | 叉腰 | 生气、得意、质问 |
| `point` | 单手指向 | 指责、指示、介绍 |
| `hug` | 双手环抱 | 安慰、亲密、拥抱 |
| `wave` | 单手挥动 | 告别、打招呼 |

---

## 节奏规范（重要！）

| 事件类型 | 之后最少等待 | 原因 |
|---------|------------|------|
| narr（旁白） | 3-4 秒 | 观众需要读完文字 |
| dialogue（对话） | 3-4 秒 | 观众需要读完台词 |
| enter（入场） | 1.5 秒 | 观众需要认识新角色 |
| emoji | 1.5 秒 | 让 emoji 动画播完 |
| label（换场） | 2 秒 | 让观众意识到场景变了 |
| exit（退场） | 1 秒 | 过渡自然 |

**总时长参考**：每 100 字文本 ≈ 10-15 秒动画时长。

---

## 角色定义

```javascript
const CHARS = {
    charId: {
        color: '#ec4899',   // 唯一颜色
        label: '角色名',    // 头顶名牌
        scale: 1,           // 缩放（小孩用 0.7）
    },
};
```

**颜色分配**：
- 主角/女主：粉色 `#ec4899`
- 温柔角色：紫色 `#7c3aed`
- 年幼角色：金色 `#f59e0b`
- 高贵角色：红色 `#dc2626`
- 冷静角色：青色 `#0891b2`
- 反面角色：深红 `#991b1b`
- 配角：灰色 `#6b7280`

---

## SVG 素材使用

**用途**：仅用于场景装饰（花/灯/植物/家具），不用于角色。

**加载方式**（必须用 data URI，不能用 Blob URL）：

```javascript
async function loadSVG(path, color, fill) {
    const resp = await fetch('../assets/' + path);
    let svg = await resp.text();
    svg = svg.replace(/stroke="currentColor"/g, `stroke="${color}"`);
    svg = svg.replace(/fill="none"/g, `fill="${fill}" fill-opacity="0.3"`);
    const img = new Image();
    img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svg)));
    await new Promise(r => { img.onload = r; });
    return img;
}
```

**绘制**：`ctx.drawImage(img, x, y, width, height)` + `ctx.globalAlpha` 控制透明度。

**推荐装饰尺寸**：30-60px，透明度 0.5-0.8。

---

## 从文本生成时间轴的 Prompt

```
你是一个动画导演。用户输入一段文本，你输出时间轴 JSON。

规则：
1. 识别所有角色，分配 id 和颜色
2. 按文本顺序生成事件，注意节奏（参考节奏规范表）
3. 角色说话 → dialogue，描述文字 → narr
4. 每句对话前给说话角色弹 emoji
5. 场景变化 → label（会自动清除旧对话）
6. 角色进出场 → enter/exit
7. 情绪变化 → arm 姿态 + emoji
8. 总时长 = 文本字数 / 8 秒（约每秒 8 字的阅读速度）

emoji 参考：
😊😄🥰😋🎉 开心
😤🤬😠 生气
😢😭🥺 悲伤
😱😵‍💫🤯 惊讶
🤔💭 思考
🚶👋🤝💪 动作
🍊🍲🧳📖🍰🍳 物品

输出：
{
  "chars": { "id": { "color": "#hex", "label": "名字", "scale": 1 } },
  "timeline": [ { "t": 0, "action": "...", ... } ]
}
```

---

## 录制导出

```python
# record_demo6.py 的核心逻辑：
# 1. Playwright 打开页面，开启 recordVideo
# 2. 等待动画播完（总时长 + 3秒缓冲）
# 3. 关闭页面，得到 .webm
# 4. ffmpeg 转 mp4：
#    ffmpeg -i input.webm -c:v libx264 -preset fast output.mp4
```

---

## 已知限制

1. 火柴人无法表达复杂肢体动作（舞蹈、打斗）
2. 同时在场角色建议 ≤ 5-6 个
3. SVG 装饰是静态的
4. 没有音效/BGM
5. 时间轴预生成，不支持交互分支
6. Canvas 文字不支持自动换行（长旁白用 DOM 字幕条）

---

## 开发命令

```bash
# 本地预览
cd workspaces/AutoMovie
python -m http.server 8899
# 访问 http://localhost:8899/demo6/index.html

# 录制视频
python record_demo6.py
# 需要：playwright + ffmpeg
```
