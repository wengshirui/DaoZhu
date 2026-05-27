# 🎭 AutoMovie 素材库

> 话剧导演系统的实体资源目录，供 AI 和开发者查找使用。

---

## 📁 目录结构

```
assets/
├── characters/       # 角色（人物）
│   ├── male/         # 男性角色
│   └── female/       # 女性角色
├── props/            # 道具（可交互物件）
│   ├── furniture/    # 家具（床、桌、椅）
│   └── items/        # 小物件（杯子、书、手机）
├── scenes/           # 场景背景
│   ├── indoor/       # 室内（卧室、客厅、办公室）
│   └── outdoor/      # 室外（街道、公园）
├── effects/          # 特效（气泡、光效、表情符号）
└── README.md         # 本文件
```

---

## 🎨 风格规范

| 属性 | 要求 |
|------|------|
| 格式 | SVG（矢量，可缩放） |
| 风格 | 手绘简笔画 / 扁平插画 / 暖色调 |
| 尺寸 | viewBox 统一为 `0 0 100 100`（等比缩放） |
| 颜色 | 使用 CSS 变量或可替换的 fill 属性 |
| 命名 | `类型-名称-状态.svg`（如 `human-male-standing.svg`） |

---

## 📋 实体注册表

每个实体需要在此登记，AI 导演根据此表选择素材：

### 🏔️ 自然 (nature/) — 21 个

| 子目录 | 文件 | 描述 |
|--------|------|------|
| mountains/ | mountain.svg, mountain-snow.svg, mountain-filled.svg | 山峰、雪山 |
| trees/ | tree-pine.svg, tree-deciduous.svg, trees.svg, flower.svg, leaf.svg, plant.svg | 松树、落叶树、树林、花、叶、植物 |
| water/ | droplets.svg, ripple.svg | 水滴、涟漪 |
| sky/ | sun.svg, moon.svg, cloud.svg, star.svg, sunrise.svg, sunset.svg, rainbow.svg | 太阳、月亮、云、星、日出、日落、彩虹 |

### 🐾 动物 (animals/) — 13 个

| 子目录 | 文件 | 描述 |
|--------|------|------|
| common/ | cat.svg, dog.svg, bird.svg, fish.svg, rabbit.svg, squirrel.svg, turtle.svg, snail.svg | 猫狗鸟鱼兔松鼠龟蜗牛 |
| wild/ | bug.svg, deer.svg, horse.svg, butterfly.svg, fish-wild.svg | 虫鹿马蝴蝶鱼 |

### 🏠 建筑 (buildings/) — 11 个

| 子目录 | 文件 | 描述 |
|--------|------|------|
| houses/ | house.svg, building.svg, building-2.svg, warehouse.svg, church.svg, castle.svg, home-filled.svg | 房屋、建筑、高楼、仓库、教堂、城堡 |
| structures/ | fence.svg, landmark.svg, tower.svg | 栅栏、地标、塔 |

### 🪑 道具 (props/) — 24 个

| 子目录 | 文件 | 描述 |
|--------|------|------|
| furniture/ | bed.svg, bed-single.svg, sofa.svg, armchair.svg, lamp.svg, lamp-desk.svg, armchair-filled.svg | 床、沙发、椅、灯 |
| doors/ | door-open.svg, door-closed.svg, door.svg, door-enter.svg, door-exit.svg | 门（开/关/进/出） |
| items/ | book-open.svg, book.svg, cup.svg, clock.svg, key.svg, phone.svg, tv.svg, laptop.svg, cooking-pot.svg, scissors.svg, umbrella.svg, utensils.svg | 书、杯、钟、钥匙、手机、电视等 |

### 👤 角色 (characters/) — 16 个

| 子目录 | 文件 | 描述 |
|--------|------|------|
| people/ | person.svg, person-round.svg, people.svg, baby.svg, person-standing.svg, person-walking.svg, person-running.svg, man.svg, woman.svg | 人物各姿态 |
| expressions/ | smile.svg, frown.svg, laugh.svg, angry.svg, meh.svg, mood-happy.svg, mood-sad.svg | 表情 |

### ✨ 特效 (effects/) — 16 个

| 子目录 | 文件 | 描述 |
|--------|------|------|
| weather/ | rain.svg, snow.svg, lightning.svg, wind.svg, fog.svg, hot.svg, snowflake.svg | 天气效果 |
| emotions/ | heart.svg, sparkles.svg, zap.svg, flame.svg, music.svg, speech.svg, idea.svg | 情感/氛围 |
| actions/ | hand.svg, hand-helping.svg, footprints.svg, move.svg, rotate.svg, arrows-move.svg | 动作提示 |

### 🚗 交通 (vehicles/) — 6 个

| 子目录 | 文件 | 描述 |
|--------|------|------|
| transport/ | car.svg, bike.svg, bus.svg, train.svg, ship.svg, plane.svg | 汽车、自行车、公交、火车、船、飞机 |

---

## 🌐 推荐外部素材源（免费可商用）

### CC0（公共领域，无需署名）

| 资源 | 链接 | 适合用途 |
|------|------|---------|
| **Open Peeps** | https://www.openpeeps.com/ | 手绘人物，可组合头/身/腿 |
| **Kenney Assets** | https://kenney.nl/assets | 游戏角色、家具、场景 |
| **Kenney Shape Characters** | https://kenney-assets.itch.io/shape-characters | 简约几何角色 |
| **SVG Repo** | https://www.svgrepo.com/ | 50万+ SVG 图标 |
| **OpenGameArt** | https://opengameart.org/ | 游戏精灵表 |

### MIT / 免费商用

| 资源 | 链接 | 适合用途 |
|------|------|---------|
| **unDraw** | https://undraw.co/ | 扁平风场景插画 |
| **illlustrations** | https://illlustrations.co/ | 开源插画 |
| **DrawKit** | https://drawkit.com/ | 手绘风插画 |
| **Flowbite Illustrations** | https://flowbite.com/illustrations/ | SVG 插画集 |

### 像素风（备选方向）

| 资源 | 链接 | 适合用途 |
|------|------|---------|
| **LPC Sprite Generator** | https://liberatedpixelcup.github.io/ | 在线生成像素角色 |
| **GDQuest Sprites** | https://github.com/GDQuest/game-sprites | Godot 友好精灵 |

---

## 🔧 AI 使用指南

当 AI 导演需要新实体时，按以下流程：

1. **查表** — 先查本 README 的注册表，看是否已有素材
2. **下载** — 如果没有，从推荐源下载 SVG
3. **适配** — 调整 viewBox 为 `0 0 100 100`，颜色改为可配置
4. **注册** — 在本 README 的注册表中添加条目
5. **使用** — 在 `entities.js` 中用 `drawImage()` 加载

### SVG 加载示例

```javascript
// 预加载 SVG 为 Image 对象
const img = new Image();
img.src = 'assets/characters/male/male-xiaoming-standing.svg';

// 在 Canvas 中绘制
ctx.drawImage(img, x, y, width, height);
```

### 状态切换示例

```javascript
// 实体定义
const xiaoming = {
    states: {
        standing: 'assets/characters/male/male-xiaoming-standing.svg',
        sitting: 'assets/characters/male/male-xiaoming-sitting.svg',
        lying: 'assets/characters/male/male-xiaoming-lying.svg',
        walking: 'assets/characters/male/male-xiaoming-walking.svg',
    },
    currentState: 'standing',
    image: new Image(),
    
    setState(state) {
        this.currentState = state;
        this.image.src = this.states[state];
    }
};
```

---

## 📝 贡献规则

- 所有素材必须是 **CC0 / MIT / 免费商用** 协议
- 文件名使用英文小写 + 连字符
- 每个新素材必须在本 README 注册表中登记
- 保持风格一致（手绘暖色调优先）
