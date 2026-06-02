# 059 — 会话自动压缩（长对话不丢上下文）

> 来源: DeepSeek-Reasonix 项目 `internal/agent/compact.go`
> 状态: 🆕 待开发
> 优先级: P1
> T-shirt Size: M
> 录入日期: 2026-06-02

---

## 问题陈述

岛主的 Agent 在长对话中（10+ 轮工具调用）会逐渐逼近模型 context window 上限。
当前没有压缩机制，到达上限后：
- 要么被截断（丢失早期上下文，AI "失忆"）
- 要么报错终止
- 要么 token 成本剧增（每轮都带全量历史）

用户在执行复杂任务（如创建工作区、连续调试）时经常遇到这个问题。

## 用户故事

**As a** 岛主用户
**I want** 长对话时 AI 不会突然"失忆"或报错
**So that** 我可以在一轮对话中完成复杂的多步骤任务，不用中途开新对话

## 范围

### In Scope

- 检测当前 prompt 接近 context window 上限时触发压缩
- 用 LLM 将旧历史总结为结构化摘要
- 保留最近 N 轮原始对话（确保当前任务上下文完整）
- 压缩后继续对话，用户无感知（或仅有轻提示）
- 压缩前归档原始历史（可追溯）

### Out of Scope

- 跨对话的记忆系统（已有 memory_service）
- 手动触发压缩（后续可加 /compact 命令）
- 配置 context window 大小（初期硬编码 DeepSeek 的 64K）

## 验收标准

1. **AC1**: 当对话 prompt tokens 超过 context window 的 75% 时自动触发压缩
2. **AC2**: 压缩后保留最近 8 轮原始消息 + 之前所有历史的结构化摘要
3. **AC3**: 摘要结构包含：Goal / Decisions / Files & code / Errors / Next step
4. **AC4**: 压缩过程对用户不可见（不中断流式输出），或仅显示"💭 整理中..."
5. **AC5**: 压缩后 AI 仍能引用早期对话中的关键信息（如用户的需求、已做的决定）
6. **AC6**: 原始被压缩的消息保存到数据库（active=0 或单独的 archive 表）

## 业务价值

- 消除长对话"撞墙"问题（预估影响 20% 的复杂任务对话）
- 减少 token 消耗（压缩后每轮不再带全量历史）
- 提升用户对 AI 能力的信任感（不再"失忆"）

## T-Shirt Size

**M** — 需改造 agent 循环（添加压缩检测点）+ 设计压缩 prompt + 归档机制；
中等复杂度，依赖 token 计数（可从 API usage 响应获取）

## 依赖

- #058 前缀缓存优化（压缩后前缀仍需保持稳定）
- 现有 chat_db 的 active 字段机制（已有 #056）
- agent.py 核心循环

## 技术提示（供开发参考）

参考 Reasonix `internal/agent/compact.go` 的完整实现：

**触发条件：**
```python
compact_ratio = 0.75  # prompt 达 75% window 时触发
context_window = 64000  # DeepSeek 的 64K（从 API 响应 usage 获取实际值）
if usage.prompt_tokens > context_window * compact_ratio:
    do_compact()
```

**压缩 Prompt（直接复用 Reasonix 的模板）：**
```
你正在压缩一个编码助手的早期对话。助手只保留你的摘要（原始消息会被删除），
所以它必须能仅凭摘要继续工作。

按以下标题输出，没有内容的标题跳过：

## Goal - 用户的请求和意图
## Decisions & rationale - 已做的决定和原因
## Files & code - 读过或修改过的文件
## Commands & outcomes - 执行过的命令和结果
## Errors & fixes - 遇到的错误和解决方式
## Pending & next step - 待完成的工作和下一步

规则：简洁 — 用列表不用散文。精确保留标识符、路径和数字。
```

**压缩结果处理：**
```python
messages = [system_prompt] + [summary_message] + recent_tail[-8:]
```
