# REQ-039: Playwright MCP 兜底方案

> Intake ID: 2026-05-26-playwright-mcp
> 优先级: 🟡 中

---

## 问题陈述

DuckDuckGo 对国内不友好，web_search 经常失败。需要 Playwright MCP 作为兜底，让 Agent 能打开浏览器搜索。

## 用户故事

**As a** 岛主用户，
**I want** 管理员在搜索失败时能打开浏览器帮我搜索，
**so that** 即使搜索 API 不可用也能获取信息。

## 验收标准

| # | AC |
|---|-----|
| 1 | 项目配置默认的 Playwright MCP server |
| 2 | web_search 失败时自动降级到 Playwright 打开浏览器搜索 |
| 3 | Playwright 操作结果返回给 Agent 继续处理 |

## T-Shirt Size

**L (8 pts)** — MCP 协议集成 + Playwright 进程管理 + 降级逻辑

---
