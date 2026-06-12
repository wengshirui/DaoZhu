# 083 — 火柴人剧场音画升级（GLM-Image + GLM-TTS）

> 状态: ✅ 已细化
> 优先级: P1
> T-shirt Size: L — 跨多模态 API 集成 + 音视频合成流水线 + 双模式切换
> 录入日期: 2026-06-12
> 来源: 复活 #046 + 智谱 GLM 多模态模型 + Pixelle-Video 参考

---

## 问题陈述

当前火柴人剧场（AutoMovie 工作区）只输出无声 HTML 动画。用户想分享到社交平台（小红书/B站）时缺少配音和画面质感，无法作为"成品视频"使用。

## 用户故事

**As a** 岛主用户（个人娱乐+社交分享）
**I want** 火柴人剧场能自动生成 AI 配音、场景插图和背景音乐，导出完整 MP4
**So that** 我一句话输入故事就能得到可直接发社交平台的有声动画短视频

---

## 范围

### In Scope

- **三级模式设计**：简单模式（SVG 无声，零成本）→ 中级模式（Pexels 视频 + Edge-TTS，免费）→ 高级模式（GLM-Image + GLM-TTS，付费最优质）
- **GLM-Image 场景图生成**：高级模式下为每个场景生成 AI 背景插图（风格统一）
- **Pexels 动态背景视频**：中级模式下按关键词搜索免费高清视频片段作为动态背景
- **GLM-TTS 角色配音**：高级模式，导演配置角色性别/声色，零样本语音克隆
- **Edge-TTS 基础配音**：中级模式，免费微软语音（无需 Key）
- **BGM 背景音乐**：预置免费 BGM 库 + 按场景氛围标签自动匹配（参考 Pixelle-Video）
- **MP4 视频导出**：ffmpeg 合成动画画面 + 配音 + BGM → MP4
- **工作区级 Key 配置**：高级模式需要在工作区设置中配置 GLM API Key
- **参考 Pixelle-Video 的 pipeline 架构和提示词设计**

### Out of Scope

- AI 音乐生成（GLM 暂无音乐模型，用预置库方案）
- 视频在线编辑/剪辑功能
- 多平台自动发布（只导出文件，用户自行上传）
- 简单模式的 HTML 动画改造（保持原样）


---

## 开放问题（已全部回答）

| # | 问题 | 答案 |
|---|------|------|
| 1 | 用户群体？ | 个人娱乐 + 社交分享（小红书/B站短视频） |
| 2 | 等待时间容忍度？ | 根据导演设计，3-5 分钟可接受 |
| 3 | AI 画图替换还是并存？ | 并存 — 简单模式先预览（零成本），高级模式出精品（需 GLM Key） |
| 4 | 未配 Key 时？ | 降级到简单模式，配了 Key 后解锁高级模式 |
| 5 | 角色配音分配？ | 导演（主 LLM）负责配置角色性别和声色，用户可手动调整 |
| 6 | BGM 来源？ | 预置免费 BGM 库 + 按氛围标签匹配（参考 Pixelle-Video），GLM 无音乐模型 |
| 7 | 输出格式？ | 最终导出 MP4（与现有火柴人剧场交付物一致） |

---

## 验收标准

### 三级模式切换

1. **AC1**: 未配任何 Key → 简单模式（SVG 无声 HTML），零成本秒出
2. **AC2**: 配置 Pexels Key → 解锁中级模式（动态视频背景 + Edge-TTS 免费配音）
3. **AC3**: 配置 GLM Key → 解锁高级模式（AI 生成插图 + GLM-TTS 零样本配音）
4. **AC4**: 简单模式生成速度保持不变（< 10 秒），用户可快速预览剧情效果

### Pexels 动态背景视频（中级模式）

5. **AC5**: 按场景关键词调用 Pexels Video API 搜索 1080p+ 免费视频片段
6. **AC6**: 每帧背景视频时长与 TTS 配音时长对齐（裁剪或循环播放）
7. **AC7**: 支持 API Key 轮换（多 Key 配置防限流，参考 MoneyPrinterTurbo）
8. **AC8**: 下载的视频缓存到本地（URL hash 命名），避免重复下载
9. **AC9**: Pexels 搜索无结果时降级到 SVG 背景，不阻塞

### GLM-Image 场景图（高级模式）

10. **AC10**: 每个场景调用 GLM-Image 生成背景插图，替代 CSS 渐变背景
11. **AC11**: 场景描述 prompt 由导演 LLM 根据剧本自动生成
12. **AC12**: GLM-Image 失败时降级到 Pexels 视频 → SVG（三级降级链）

### TTS 配音

13. **AC13**: 中级模式使用 Edge-TTS（免费微软语音），无需任何 Key
14. **AC14**: 高级模式使用 GLM-TTS（零样本克隆，情感可控）
15. **AC15**: 导演 LLM 分析剧本后为每角色分配性别/声色（结构化 JSON）
16. **AC16**: 旁白使用默认中性音色，区别于角色对话
17. **AC17**: TTS 调用失败时该段静音处理（生成等时长静音 mp3），不阻塞

### BGM 背景音乐

18. **AC18**: 工作区内置 29 首免费 BGM，按氛围标签分类（欢快/悲伤/紧张/温馨/史诗）
19. **AC19**: 导演 LLM 为每场景标注氛围标签，BGM 据此自动匹配
20. **AC20**: BGM 音量自动压低（-6dB）当配音播放时（ducking），配音结束恢复
21. **AC21**: BGM 循环播放至视频结束，最后 3 秒淡出

### 字幕

22. **AC22**: MP4 输出包含硬编码字幕，对话/旁白与配音时间同步
23. **AC23**: 字幕使用内置微软雅黑字体，底部居中，半透明黑底白字
24. **AC24**: Edge-TTS 模式通过 WordBoundary 事件获取逐词时间戳生成精确字幕

### 视频合成

25. **AC25**: ffmpeg 合成：逐帧视频片段拼接 + 配音对齐 + BGM 混音 + 字幕烧录 → MP4
26. **AC26**: 支持三种分辨率：竖屏 1080×1920、横屏 1920×1080、方形 1080×1080
27. **AC27**: 视频编码优先 h264_nvenc（GPU 加速），不可用时回退 libx264
28. **AC28**: 整体生成时间 ≤ 5 分钟（30 秒剧本基准）

### 阶段可停（stop_at）

29. **AC29**: 用户可停在"分镜预览"阶段（只看剧本+角色配置，不花 API 额度）
30. **AC30**: 确认分镜后继续生成，支持从断点恢复（分镜 JSON 持久化到文件）

### 进度与状态管理

31. **AC31**: 每个阶段更新进度百分比（5%→20%→50%→80%→100%），前端可展示进度条
32. **AC32**: 任何阶段失败 → 状态标记为 FAILED + 错误原因，已完成的资产保留不删除

### 错误路径

33. **AC33**: ffmpeg 未安装时提示安装地址，不崩溃
34. **AC34**: 网络中断导致所有 API 失败 → 整体降级到简单模式输出 HTML
35. **AC35**: 单帧资产失败不影响其他帧（帧级隔离，参考 Pixelle-Video 设计）


---

## 业务价值

- 从"玩具级 demo"升级为"可分享的成品" — 直接提升工作区的实用价值
- 用户获取成本：一句话输入 → 3-5 分钟 → 拿到可发 B 站/小红书的短视频
- 复用 GLM 生态（智谱已有免费额度），用户零硬件要求
- 为岛主积累多模态 AI 集成能力（图/音/视频 pipeline）

---

## 生成流程（参考 Pixelle-Video flow.png）

```
用户输入故事文本
      ↓
┌─────────────────────────────────────────┐
│ Stage 1: 导演分析（LLM）                │
│  - 拆分场景 + 角色识别                   │
│  - 为每场景标注氛围标签                  │
│  - 为每角色配置性别/声色                 │
│  - 生成场景描述 prompt（供 GLM-Image）   │
│  - 输出：分镜 JSON（Storyboard）         │
└─────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────┐
│ Stage 2: 资产生成（按帧并行）           │
│  每帧分镜独立处理：                      │
│  ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │GLM-Image │ │ GLM-TTS  │ │  BGM   │  │
│  │场景背景图│ │角色配音  │ │氛围匹配│  │
│  └──────────┘ └──────────┘ └────────┘  │
│  某帧失败不阻塞其他帧（降级到简单模式） │
└─────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────┐
│ Stage 3: 动画渲染                       │
│  - 火柴人动画帧生成（HTML→截图/录制）   │
│  - 叠加 AI 场景背景图                    │
│  - 每帧时长由 TTS 音频长度决定           │
└─────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────┐
│ Stage 4: 后期合成（ffmpeg）             │
│  - 逐帧视频片段拼接                     │
│  - 配音对齐 + BGM 混音                   │
│  - 导出 MP4（1080p，30fps）             │
└─────────────────────────────────────────┘
      ↓
   输出 MP4 文件
```

### 分镜数据结构（参考 Pixelle-Video Storyboard）

每个场景（帧）包含以下字段：

| 字段 | 来源 | 说明 |
|------|------|------|
| index | 导演分析 | 帧序号 |
| narration | 导演分析 | 旁白/对话文字 |
| characters | 导演分析 | 角色列表（位置、动作、表情） |
| mood_tag | 导演分析 | 氛围标签（欢快/悲伤/紧张...） |
| image_prompt | 导演分析 | 场景背景图 prompt |
| audio_path | Stage 2 | TTS 合成的语音文件路径 |
| image_path | Stage 2 | GLM-Image 生成的背景图路径 |
| bgm_segment | Stage 2 | 匹配的 BGM 片段 |
| duration | Stage 2 | 帧时长（由 TTS 音频决定） |
| video_segment | Stage 3 | 合成的该帧视频片段 |

**核心设计原则：**
- 分镜是流水线各阶段间的**契约** — 导演输出它，后续阶段消费它
- 每帧独立处理，支持并行生成
- 任意帧失败 → 该帧降级到简单模式，不影响整体

---

## 技术参考

| 参考源 | 复用内容 |
|--------|---------|
| **MoneyPrinterTurbo** task.py | Pipeline 状态机 + stop_at 阶段可停 + 进度百分比更新 |
| **MoneyPrinterTurbo** material.py | Pexels Video API 集成：搜索→筛选分辨率→下载→URL hash 缓存 |
| **MoneyPrinterTurbo** voice.py | Edge-TTS 封装：SubMaker 字幕时间戳 + 超时重试 + 静音兜底 |
| **MoneyPrinterTurbo** video.py | ffmpeg 合成：concat demuxer + BGM ducking + 字幕烧录 + codec fallback |
| **MoneyPrinterTurbo** llm.py | LLM 搜索词生成 prompt 设计 + JSON 解析容错 |
| Pixelle-Video pipeline 架构 | 文案→配图规划→逐帧处理→视频合成的阶段化设计 |
| Pixelle-Video storyboard.py | 分镜数据结构（Frame + progress tracking） |
| Pixelle-Video services/video.py | ffmpeg-python 合成流程（concat + BGM loop + fade） |
| GLM-Image API | 场景图生成（bigmodel.cn OpenAI 兼容格式） |
| GLM-TTS API | 角色配音（零样本克隆、情感可控） |

### 从 MoneyPrinterTurbo 学到的关键模式

1. **API Key 轮换** — 多 Key 配置 + 线程安全计数器轮换，防限流
2. **视频缓存** — URL hash 命名本地文件，存在则跳过下载
3. **TTS 超时保护** — Edge-TTS 用 daemon 线程 + Queue 做超时控制（30s）
4. **静音兜底** — TTS 完全失败时用 ffmpeg `anullsrc` 生成等时长静音 mp3
5. **编码器回退** — 优先 h264_nvenc → 失败则 libx264，运行时禁用失败编码器
6. **进度状态机** — 每阶段更新 progress%，状态只有 PROCESSING/COMPLETE/FAILED
7. **字幕时间戳** — Edge-TTS 的 WordBoundary 事件提供逐词时间，字幕精度极高

---

## 影响的文件

| 文件/目录 | 改动 |
|-----------|------|
| `workspaces/AutoMovie/generator.py` | 重构 — 加入 pipeline 阶段化设计 |
| `workspaces/AutoMovie/storyboard.py` | 已创建 — 分镜数据结构 |
| `workspaces/AutoMovie/glm_config.py` | 已创建 — GLM Key 配置管理 |
| `workspaces/AutoMovie/glm_image.py` | 已创建 — GLM-Image 场景图生成 |
| `workspaces/AutoMovie/glm_tts.py` | 已创建 — GLM-TTS 角色配音 |
| `workspaces/AutoMovie/pexels_service.py` | 新增 — Pexels API 搜索场景图 |
| `workspaces/AutoMovie/edge_tts_service.py` | 新增 — Edge-TTS 免费配音（降级方案） |
| `workspaces/AutoMovie/video_service.py` | 新增 — ffmpeg 合成 + 字幕烧录 |
| `workspaces/AutoMovie/bgm/` | 已创建 — 29 首预置 BGM（来源 MoneyPrinterTurbo） |
| `workspaces/AutoMovie/fonts/` | 已创建 — 7 个字体文件（含微软雅黑，用于字幕） |
| `workspaces/AutoMovie/frontend/` | 修改 — 三级模式切换 + Key 配置入口 |
| `workspaces/AutoMovie/workspace.json` | 修改 — 新增配置字段 |

---

## 依赖

- ffmpeg（系统级，合成视频必须）
- 智谱 GLM API Key（bigmodel.cn，高级模式必须）
- Pixelle-Video（参考代码和提示词，不引入为运行时依赖）
- #082 Agent 自动控制系统（已完成，导演 LLM 复用 agent 架构）
