# QA Sign-Off: 岛主平台 v0.2.0 回归测试

**Date**: 2026-05-26
**Status**: PASS（有已知限制）

---

## API 端点测试

| 端点 | 方法 | 结果 |
|------|------|------|
| /api/workspaces | GET | ✅ 200 |
| /api/skills | GET | ✅ 200 |
| /api/tools | GET | ✅ 200 |
| /api/conversations | GET | ✅ 200 |
| /api/config | GET | ✅ 200 |
| /api/memory/profile | GET | ✅ 200 |
| /api/chat (正常) | POST | ✅ 200 |
| /api/chat (空消息) | POST | ✅ 400 |
| /api/workspaces/todo/start | POST | ✅ 启动成功 |
| /api/workspaces/todo/stop | POST | ✅ 停止成功 |
| todo HTTP 7801 | GET | ✅ 200 |
| /onboarding | GET | ✅ 200 |
| /favicon.svg | GET | ✅ 200 |
| /img/librarian.svg | GET | ✅ 200 |

---

## 边缘情况

| # | 场景 | 结果 |
|---|------|------|
| 1 | 空消息发送 | ✅ 返回 400 |
| 2 | 启动不存在的工作区 | ✅ 返回 404 |
| 3 | 工作区启动后 HTTP 可达 | ✅ |
| 4 | 工作区停止后进程清理 | ✅ |

---

## 已知限制（非阻塞）

| 问题 | 影响 | 状态 |
|------|------|------|
| web_search DuckDuckGo 国内不稳定 | 搜索可能失败 | 有 browser_search 兜底 |
| lightweight 模式挂载不稳定 | todo 改回 standard | 后续优化 |
| DeepSeek 偶尔返回空 arguments | 工具调用可能失败 | 有必填参数校验+重试提示 |

---

## 回归测试

- 核心 API: ✅ 全部通过
- 工作区生命周期: ✅ 启停正常
- 聊天功能: ✅ SSE 流式正常
- 数据库初始化: ✅ chat.db + memory.db + config.db 自动创建
