# 🎭 火柴人剧场

> 文本转动画：输入故事，AI 生成火柴人动画，导出 HTML/MP4。

## 功能

1. **输入文本** — 粘贴小说/散文/剧本，或上传 .txt 文件
2. **AI 生成** — 自动识别角色、分配颜色、编排时间轴
3. **预览播放** — 生成独立 HTML 文件，双击即可播放
4. **导出视频** — 通过 Playwright 录制为 mp4（需要 ffmpeg）

## 设计原则

**Less is More — 火柴人 + emoji + 时间轴**

- 角色 = 颜色区分的火柴人（圆头 + 线条）
- 情感 = emoji 弹出
- 动作 = 手臂姿态 + 位移 + 走路摆动
- 场景 = 渐变背景 + SVG 装饰
- 叙事 = 底部字幕条（旁白 + 对话统一位置）
- 节奏 = 时间轴连续播放，每段留 3-4 秒阅读时间

## 文件结构

```
workspaces/AutoMovie/
├── workspace.json      # 工作区配置
├── app.py              # FastAPI 入口（轻挂载）
├── routes.py           # API 路由
├── generator.py        # AI 生成 + HTML 渲染
├── template.html       # 动画 HTML 模板（含内嵌引擎）
├── frontend/           # 用户界面
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── assets/             # SVG 素材库（107个）
├── output/             # 生成的动画文件
├── examples/           # 示例文本
├── example/            # demo6 示例代码
├── AGENT.md            # AI Agent 开发指南
└── README.md           # 本文件
```

## 使用方式

### 通过主平台（推荐）

工作区以轻挂载模式运行在主平台 `/ws/stickman-theater/`。

### 独立运行

```bash
cd workspaces/AutoMovie
python -m uvicorn app:app --port 7805
```

### 导出 MP4

```bash
# 需要安装 playwright 和 ffmpeg
python -c "
from playwright.sync_api import sync_playwright
import subprocess
with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(record_video_dir='output/', record_video_size={'width':960,'height':580})
    page = ctx.new_page()
    page.goto('file:///path/to/output/xxx.html')
    page.wait_for_timeout(95000)
    page.close(); ctx.close(); browser.close()
# 然后 ffmpeg -i output/xxx.webm -c:v libx264 output/xxx.mp4
"
```
