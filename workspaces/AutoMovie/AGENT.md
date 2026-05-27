# 🧠 AutoMovie 开发指南

> 面向 AI Agent 和开发者的技术文档。生成动画时遵循此文档。

---

## 核心原则：Less is More

**不要追求写实。用最简单的视觉元素传达故事。**

| 要素 | 正确做法 | 错误做法 |
|------|---------|---------|
| 角色 | 火柴人（圆头+线条），颜色区分 | 画五官、衣服褶皱、头发 |
| 情感 | emoji 弹出在头顶 | 画复杂面部表情 |
| 动作 | 手臂姿态 + 位移 + 抖动 | 骨骼动画、关节旋转 |
| 场景 | 渐变背景 + 少量 SVG 装饰 | 画满建筑细节 |
| 叙事 | 底部字幕条（旁白+对话） | 分散的气泡框 |
| 节奏 | 时间轴连续播放 | 一幕一幕硬切 |

---

## 技术架构

```
┌─────────────────────────────────────────┐
│  Canvas 层（每帧重绘）                    │
│  - 背景渐变                              │
│  - SVG 装饰（drawImage）                 │
│  - 火柴人角色                            │
├─────────────────────────────────────────┤
│  DOM 层（CSS 动画）                       │
│  - emoji 弹出（.emoji-pop）              │
│  - 字幕条（旁白 + 对话）                  │
│  - 场景标签                              │
│  - 进度/控制栏                           │
└─────────────────────────────────────────┘
```

---

## 时间轴格式

动画由一个事件数组驱动，每个事件有 `t`（毫秒时间戳）和 `action`：

```javascript
const TIMELINE = [
    { t: 0,    action: 'label', text: '📍 场景名' },
    { t: 0,    action: 'narr',  text: '旁白文字' },
    { t: 500,  action: 'enter', id: 'charId', x: 450, y: 280 },
    { t: 1200, action: 'emoji', id: 'charId', e: '😊' },
    { t: 2000, action: 'dialogue', who: '角色名', text: '"台词"' },
    { t: 3000, action: 'arm',   id: 'charId', arm: 'point' },
    { t: 4000, action: 'move',  id: 'charId', x: 300 },
    { t: 5000, action: 'exit',  id: 'charId' },
    { t: 6000, action: 'end' },
];
```

### 可用 action 类型

| action | 参数 | 说明 |
|--------|------|------|
| `enter` | id, x, y | 角色入场（从屏幕外滑入） |
| `exit` | id | 角色退场（滑出屏幕） |
| `move` | id, x, y? | 角色移动到新位置 |
| `arm` | id, arm | 改变手臂姿态 |
| `emoji` | id, e | 角色头顶弹出 emoji |
| `dialogue` | who, text | 显示对话（底部白色条） |
| `narr` | text | 显示旁白（底部深色条） |
| `label` | text | 更新场景标签 |
| `end` | — | 动画结束 |

### 手臂姿态 (arm)

| 值 | 含义 | 适用场景 |
|----|------|---------|
| `normal` | 自然下垂 | 默认 |
| `up` | 双手举起 | 欢呼、投降、攀爬 |
| `hip` | 叉腰 | 生气、得意 |
| `point` | 指向 | 指责、指示 |
| `hug` | 拥抱/环抱 | 安慰、亲密 |
| `wave` | 挥手 | 告别、打招呼 |

---

## 角色定义

```javascript
const CHARS = {
    charId: {
        color: '#ec4899',   // 角色颜色（唯一标识）
        label: '角色名',    // 头顶名牌
        scale: 1,           // 缩放（小孩用 0.7）
    },
};
```

**颜色分配建议**：
- 主角：粉色/蓝色（暖色调）
- 正面角色：紫色/金色/红色
- 反面角色：深红/暗色
- 配角：青色/灰色

---

## SVG 素材使用

素材在 `assets/` 目录，通过 fetch + 颜色注入加载：

```javascript
async function loadSVG(path, strokeColor, fillColor) {
    const resp = await fetch('../assets/' + path);
    let svg = await resp.text();
    // 注入颜色
    svg = svg.replace(/stroke="currentColor"/g, `stroke="${strokeColor}"`);
    svg = svg.replace(/fill="none"/g, `fill="${fillColor}" fill-opacity="0.3"`);
    // 转为 Image 对象
    const img = new Image();
    img.src = URL.createObjectURL(new Blob([svg], {type:'image/svg+xml'}));
    return img;
}
```

**用途**：场景装饰（花/灯/植物），不用于角色主体。

**注意**：SVG 素材是 UI 图标级别（Lucide/Tabler），适合做小装饰，不适合做主要实体。

---

## 场景背景

用 Canvas 渐变 + 简单几何 + SVG 装饰：

```javascript
// 宫殿
background: linear-gradient(暖黄 → 金色 → 深棕地面)
+ 两根柱子（fillRect）
+ SVG 花/灯/植物装饰

// 室外
background: linear-gradient(天蓝 → 白 → 绿色草地)
+ SVG 树/云装饰

// 车站
background: linear-gradient(灰蓝 → 土黄月台)
+ 虚线铁轨 + 矩形火车
```

---

## 从文本生成时间轴的 Prompt（给 AI 导演用）

```
你是一个动画导演。用户会输入一段文本（小说/散文/剧本），你需要输出一个时间轴 JSON。

规则：
1. 识别所有角色，为每个角色分配一个 id 和颜色
2. 按文本顺序生成事件，每个事件间隔 500-3000ms
3. 角色说话时用 dialogue，描述性文字用 narr
4. 每句对话前给说话角色弹一个合适的 emoji
5. 场景变化时用 label 标注地点
6. 角色进出场用 enter/exit
7. 情绪变化用 arm 姿态 + emoji 配合
8. 总时长控制在 30-60 秒

可用 emoji 参考：
- 开心：😊😄🥰😋🎉
- 生气：😤🤬😠
- 悲伤：😢😭🥺
- 惊讶：😱😵‍💫🤯
- 思考：🤔💭
- 动作：🚶👋🤝💪
- 物品：🍊🍲🧳📖🍰

输出格式：
{
  "chars": { "id": { "color": "#hex", "label": "名字" } },
  "timeline": [ { "t": 0, "action": "...", ... } ]
}
```

---

## 已知限制

1. 火柴人无法表达复杂肢体动作（如舞蹈、打斗）
2. 同时在场角色建议不超过 5-6 个（太多会拥挤）
3. SVG 装饰是静态的，不会动
4. 没有音效/BGM（纯视觉）
5. 时间轴是预生成的，不支持交互分支

---

## 开发命令

```bash
# 启动本地预览（在 AutoMovie/ 目录）
python -m http.server 8899
# 然后访问 http://localhost:8899/demo6/index.html
```
