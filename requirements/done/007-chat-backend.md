# REQ-007: AI 对话后端（聊天接口）

> Intake ID: 2025-05-25-chat-backend

---

## 原始需求

前端聊天窗口需要后端 API 支撑：接收用户消息、调用 Agent、流式返回响应、管理会话历史。

---

## 提取意图

提供 RESTful + SSE/WebSocket 接口：
- `POST /api/chat` — 发送消息，触发 Agent 处理
- `GET /api/chat/stream` — SSE 流式返回 Agent 响应
- `GET /api/conversations` — 获取历史会话列表
- `GET /api/conversations/{id}` — 获取单个会话详情
- `DELETE /api/conversations/{id}` — 删除会话

会话数据持久化到平台级 SQLite（非工作区级）。

---

## 开放问题

| # | 模块 | 问题 | AI 猜测 | 答案 |
|---|------|------|---------|------|
| 1 | 用户与现状 | 对话响应是否需要支持 Markdown 渲染（代码块、列表等）？ | 是，前端需渲染 Markdown | |
| 2 | 范围与影响 | 流式响应选择 SSE 还是 WebSocket？考虑到后续可能的实时日志推送 | WebSocket 更灵活，支持双向通信 | |
| 3 | 业务规则 | 会话历史保留多久？是否有存储上限？ | 永久保留，用户可手动删除 | |

---

## T-Shirt Size

**M (5 pts)** — 涉及流式通信、会话持久化、与 Agent 模块集成。

---

## 状态

- [x] 需求录入
- [ ] 开放问题确认
- [ ] 需求提炼
- [ ] 移交开发
