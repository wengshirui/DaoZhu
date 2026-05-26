# 🧠 开发指南：如何构建“AI导演 + 实体演员”系统

本文档面向希望二次开发或理解本项目架构的开发者。我们将从**架构设计、实体系统、剧本调度、测试方法**四个维度进行说明。

## 一、项目目标

**最终效果**：用户输入一句自然语言（例如：“小明早晨起床了，打开了门”），系统自动生成一个可交互的 Web 页面，其中：
- 舞台背景布置完成（床、门、窗户等）。
- 实体“小明”按照剧情顺序完成：躺 → 坐 → 站 → 走到门前 → 开门。
- 每一步伴随导演文字说明和角色对话气泡。

**成功标准**：
- 实体状态机正确流转。
- 门的开关状态与剧情同步。
- 用户无需任何操作即可观看完整表演。
- 支持一键重置，反复播放。

## 二、核心架构

系统分为三层：
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ 剧本层 │────▶│ 导演层 │────▶│ 执行层 │
│ (Scenes) │ │ (Scheduler) │ │ (Renderer) │
└─────────────┘ └─────────────┘ └─────────────┘

- **剧本层**：一个 JSON 数组，每个元素包含动作类型、持续时间、文字描述。可由 LLM 生成，也可手动编写。
- **导演层**：一个时序调度器，按顺序触发每个场景，并调用实体对应的“方法”。
- **执行层**：Canvas 渲染器 + 实体状态管理器，负责绘制舞台、更新实体位置/状态、显示台词。

## 三、实体系统设计

每个实体是一个 JavaScript 对象，至少包含：

```javascript
let xiaoming = {
  type: "human",
  name: "小明",
  x: 280, y: 380,
  state: "lying",           // 当前状态
  walkTargetX: null,        // 移动目标坐标
  openDoor: function() {    // 方法
    door.isOpen = true;
  }
};
采用递归计时器 + 状态机模式：
javascript

const scenes = [ ... ];
let currentIdx = 0;

function playScene(index) {
  const scene = scenes[index];
  // 1. 根据 scene.actorAction 修改实体状态
  switch(scene.actorAction) {
    case "walk_to_door": startWalking(); break;
    case "open_door": door.open(); break;
    // ...
  }
  // 2. 设置定时器，结束后播放下一场
  setTimeout(() => {
    playScene(index + 1);
  }, scene.duration);
}

注意：走路等连续动画需要在 requestAnimationFrame 中插值，但定长走路可直接在定时器回调中设置最终位置（简单场景足够）。
若要让 AI 担任导演，需要设计一个结构化输出 Prompt。示例：
text

你是一个话剧导演。用户会输入一段剧情描述，你需要输出一个 JSON 数组，
每个元素包含：action (实体动作), duration(毫秒), description(中文旁白)。

可用动作列表：["wake","sit","stand","walk_to_door","open_door","finish"]

用户输入：小明早晨起床了，打开了门。

你的输出：
[
  {"action":"wake","duration":1500,"description":"小明从睡梦中醒来"},
  {"action":"sit","duration":1000,"description":"小明坐起身"},
  {"action":"stand","duration":800,"description":"小明站起来"},
  {"action":"walk_to_door","duration":2000,"description":"小明走向房门"},
  {"action":"open_door","duration":1200,"description":"小明打开了门"}
]