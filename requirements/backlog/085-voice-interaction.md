# 085 — 语音交互（语音唤醒 + 语音对话）

> 状态: � 开发中
> 优先级: P1
> T-shirt Size: L
> 录入日期: 2026-06-15
> 来源: PO 产品构想 — 儿童场景核心通道

---

## 问题陈述

儿童不会打字，当前只能通过键盘与 agent 交互。需要语音通道让儿童（及解放双手的成人）能自然地与 agent 对话。

## 用户故事

**As a** 岛主用户（尤其是儿童）
**I want** 通过语音唤醒 agent 并进行对话
**So that** 不需要打字就能使用 agent 的所有能力

---

## 技术方案（基于开源调研）

| 组件 | 方案 | 来源 |
|------|------|------|
| STT（语音→文字） | RealtimeSTT（Whisper + VAD + 唤醒词） | KoljaB/RealtimeSTT |
| TTS（文字→语音） | Edge-TTS（已有）通过 RealtimeTTS 流式播放 | KoljaB/RealtimeTTS |
| 唤醒词 | openwakeword（RealtimeSTT 内置支持） | 自定义"岛主" |
| 整合参考 | RealtimeSTT_LLM_TTS（智谱AI+Edge-TTS） | Ikaros-521 |
| 完整参考 | RealtimeVoiceChat（WebSocket+LLM+TTS） | KoljaB |

**本地参考代码：** `references/RealtimeSTT_LLM_TTS/` + `references/RealtimeVoiceChat/`

---

## 范围

### In Scope

- 安装 RealtimeSTT + openwakeword 做唤醒词检测
- **唤醒词可配置**（默认"岛主"，用户可在设置中自定义）
- 语音转文字（Whisper tiny/base，本地运行）
- **STT 模型可选**（本地 Whisper / 云端 GLM-ASR）
- 文字送入现有 agent_chat_stream → 获取回复
- 回复通过 TTS 流式播放
- **TTS 音色可配置**（Edge-TTS 多音色 / GLM-TTS）
- **TTS 引擎可选**（Edge-TTS 免费 / GLM-TTS 高质量）
- 前端麦克风按钮（手动模式：按住说话）
- 后端 WebSocket 传输音频流
- 配置项集中在 config.json 的 `voice` 字段

### Out of Scope

- 连续对话模式（先做单轮）
- 自定义唤醒词（先固定"岛主"）
- 多语言识别（先只支持中文）
- 桌面宠物动画联动（后续 087）

---

## 验收标准

1. **AC1**: 用户点击麦克风按钮 → 开始录音 → 松开后语音转文字 → 发送给 agent
2. **AC2**: agent 回复文字后自动通过 TTS 播放语音
3. **AC3**: 唤醒词可在设置中自定义（默认"岛主"），检测到时自动开始录音
4. **AC4**: 语音识别支持中文，STT 引擎可选：本地 Whisper / 云端 GLM
5. **AC5**: TTS 音色可在设置中选择（Edge-TTS 多音色列表 + GLM-TTS）
6. **AC6**: 麦克风权限未授予时，友好提示用户授权
7. **AC7**: 网络断开时语音功能降级（本地 Whisper 仍可用，TTS 失败则只显示文字）
8. **AC8**: 所有语音配置项在 config.json 的 `voice` 字段集中管理

---

## 依赖

- RealtimeSTT >= 1.0（pip install realtimestt[openwakeword]）
- RealtimeTTS（pip install realtimetts[edge]）
- PyAudio（麦克风输入）
- 浏览器 Web Audio API（前端录音）
- WebSocket（音频流传输）
