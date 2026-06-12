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

- **三级模式设计**：简单模式（SVG 无声，零成本）→ 中级模式（Pexels 图 + Edge-TTS，免费）→ 高级模式（GLM-Image + GLM-TTS，付费最优质）
- **GLM-Image 场景图生成**：高级模式下为每个场景生成 AI 背景插图
- **Pexels 场景图搜索**：中级模式下按关键词搜索免费高清背景图
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

### 双模式

1. **AC1**: 用户未配置 GLM API Key 时，工作区默认运行简单模式（当前 SVG 无声 HTML），无报错
2. **AC2**: 用户在工作区设置中配置 GLM API Key 后，界面出现"高级模式"开关
3. **AC3**: 简单模式生成速度保持不变（< 10 秒），用户可快速预览剧情效果

### GLM-Image 场景图

4. **AC4**: 高级模式下，每个场景调用 GLM-Image 生成背景插图，替代 CSS 渐变背景
5. **AC5**: 场景描述 prompt 由导演 LLM 根据剧本自动生成（参考 Pixelle-Video 的 prompt 设计）
6. **AC6**: GLM-Image API 调用失败时，降级到 Pexels 搜索或简单模式的 SVG 背景，不阻塞流程

### Pexels 素材源（中级模式）

7. **AC7-new**: 支持 Pexels API 搜索场景背景图（免费、无版权），按场景关键词搜索匹配
8. **AC8-new**: 未配置 GLM Key 但配置了 Pexels Key 时，自动使用 Pexels 作为场景图来源
9. **AC9-new**: Pexels 搜索无结果时，降级到 SVG 简单背景


### GLM-TTS 角色配音

7. **AC7**: 导演 LLM 分析剧本后，为每个角色分配性别和声色参数（输出结构化 JSON）
8. **AC8**: 每段角色对话调用 GLM-TTS 生成语音 mp3，音色与角色配置一致
9. **AC9**: 旁白/叙述使用默认中性音色，区别于角色对话
10. **AC10**: GLM-TTS 调用失败时，该段对话静音处理，不阻塞整体流程

### BGM 背景音乐

11. **AC11**: 工作区内置 ≥ 5 首免费 BGM（欢快/悲伤/紧张/温馨/史诗），按场景氛围自动选择
12. **AC12**: 导演 LLM 为每个场景标注氛围标签，BGM 据此切换或淡入淡出
13. **AC13**: BGM 音量自动压低（-6dB）当角色配音播放时，配音结束后恢复

### 视频合成

14. **AC14**: 最终调用 ffmpeg 合成：动画画面 + 角色配音 + BGM → MP4 文件
15. **AC15**: 合成的 MP4 支持多种分辨率：竖屏 1080×1920（社交平台首选）、横屏 1920×1080、方形 1080×1080，用户可选
16. **AC16**: 整体生成时间 ≤ 5 分钟（30 秒剧本基准）

### 字幕系统（参考 MoneyPrinterTurbo）

19. **AC19**: MP4 输出包含硬编码字幕，对话/旁白文字与配音时间同步
20. **AC20**: 字幕使用工作区内置中文字体（微软雅黑），位置在底部居中

### 阶段可停（stop_at 设计）

21. **AC21**: 用户可选择只生成分镜（预览剧本 + 角色配置），确认后再继续资产生成
22. **AC22**: 分镜预览阶段不消耗 GLM API 额度（只用主 LLM 分析）

### TTS 降级方案

23. **AC23**: 默认 TTS 使用 Edge-TTS（免费），GLM-TTS 作为高级选项（声色更自然、可克隆）
24. **AC24**: 未配置 GLM Key 时用 Edge-TTS 生成配音（不是静音），配了 Key 后切换到 GLM-TTS

### 错误路径

25. **AC25**: ffmpeg 未安装时，提示用户安装地址，不崩溃
26. **AC26**: 网络中断导致 GLM API 全部失败时，整体降级到 Edge-TTS + 简单模式输出


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
| Pixelle-Video pipeline 架构 | 文案→配图规划→逐帧处理→视频合成的阶段化设计 |
| Pixelle-Video prompts/ | 场景描述 prompt 模板、脚本分割方式 |
| Pixelle-Video services/tts_service.py | TTS 调用封装模式 |
| Pixelle-Video services/video.py | ffmpeg 合成流程（concat + BGM + audio merge） |
| Pixelle-Video bgm/ | BGM 库组织方式（按氛围标签） |
| GLM-Image API | 场景图生成（bigmodel.cn） |
| GLM-TTS API | 角色配音（零样本克隆、情感可控） |

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
