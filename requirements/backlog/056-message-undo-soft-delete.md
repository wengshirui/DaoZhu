# 056 — 消息撤回（软删除 + Undo）

> 来源: hermes-agent feat(undo) / feat(state) — 2026-05-31
> 创建: 2026-06-01
> 状态: 🆕 待开发

---

## 问题陈述

用户在与岛管理员对话时，可能误发消息、发错内容、或对 AI 回复不满意想重新提问。
当前系统没有撤回能力，消息一旦发出就永久存在于对话历史中，且 AI 后续回复会基于
错误的上下文继续推理。

## 用户故事

**As a** 岛主用户
**I want** 撤回最近的一轮或多轮对话
**So that** 我可以修正错误输入，或让 AI 基于正确的上下文重新回答

## 范围

### In Scope

- 数据库层：messages 表增加 `active` 字段（软删除）
- 后端 API：`POST /api/chat/{conv_id}/undo?n=1` 撤回最近 N 轮
- 前端：消息气泡 hover 显示撤回按钮（仅最近 3 轮可撤回）
- 撤回后将被撤回的用户消息文本回填到输入框
- 查询消息时默认 `WHERE active = 1`

### Out of Scope

- 恢复已撤回消息（审计用途，后续可做）
- 撤回后通知 memory_service 清理记忆（后续优化）
- 管理员/多用户场景的撤回权限

## 验收标准

1. **AC1**: 用户点击撤回按钮后，该轮对话（用户消息 + AI 回复）从界面消失，
   输入框自动填入被撤回的用户消息文本
2. **AC2**: 撤回的消息在数据库中 `active = 0`，不会被后续 AI 调用读取到，
   但数据不物理删除
3. **AC3**: 撤回 N 轮时（N > 1），从最新往前连续撤回 N 组 user+assistant 消息对
4. **AC4**: 对话中只有 1 条消息时，撤回操作不可用（按钮灰显或隐藏）
5. **AC5**: 撤回操作响应时间 < 200ms（纯本地 SQLite 操作）

## 业务价值

- 减少用户因误发消息而新建对话的频率（预估减少 30% 的"废弃对话"）
- 提升 AI 回复质量（上下文更干净）
- 用户满意度提升（对话可控感）

## T-Shirt Size

**XS** — 纯本地 SQLite 字段变更 + 简单 API + 前端按钮；无外部依赖，无复杂逻辑

## 依赖

- chat_db.py schema 变更（加字段 + 迁移）
- agent.py 查询消息时需过滤 active = 0

## 技术提示（供开发参考）

参考 hermes-agent `hermes_state.py` 的实现：
- `messages.active` INTEGER DEFAULT 1
- `rewind_to_message()` 方法：soft-delete >= target_id 的行
- 查询方法加 `include_inactive` kwarg（默认 False）
