# REQ-017 MCP 客户端（外部工具连接器）

**状态：** ✔️ Done  
**优先级：** P1（Skill 系统的补充 — Skill 描述"怎么做"，MCP 提供"用什么做"）  
**T-Shirt Size：** L - 涉及子进程管理、异步事件循环、协议适配、工具注册；需要稳定的连接管理

---

## 问题陈述

AccoBot 内置的工具覆盖了核心财务操作，但无法覆盖所有外部系统。不同用户使用不同的财务软件（金蝶云/用友/浪潮）、不同的银行接口、不同的发票平台。MCP（Model Context Protocol）是一个标准协议，允许通过配置文件声明式地接入外部工具服务器，无需修改 AccoBot 代码。

## 用户故事

**As a** 使用金蝶云的企业财务人员  
**I want** 通过配置文件接入金蝶云的 MCP Server  
**So that** AccoBot 可以直接读写金蝶云的数据，不用我在两个系统之间手动搬运

## 范围

### In Scope

**MCP 配置：**
- 在 `~/.accobot/config.yaml` 的 `mcp_servers` 段声明 MCP Server
- 支持两种传输方式：stdio（本地子进程）和 HTTP（远程服务）
- 支持环境变量插值（`${VAR_NAME}`），敏感信息不硬编码
- Playwright MCP 作为默认预配置（开箱即用）

**MCP 连接管理：**
- Agent 启动时自动连接所有已配置且 enabled 的 MCP Server
- 每个 Server 在后台线程的 asyncio 事件循环中保持长连接
- 连接失败时自动重试（指数退避，最多 3 次）
- 支持手动重连（通过 Web UI 或命令）

**MCP 工具发现与注册：**
- 连接成功后，调用 MCP 协议的 `tools/list` 获取工具列表
- 将 MCP 工具注册到 AccoBot 的 tool registry（与内置工具统一）
- 工具名加前缀：`mcp_{server}_{tool}`（如 `mcp_playwright_browser_navigate`）
- 工具 schema 自动转换为 OpenAI function calling 格式

**MCP 工具调用：**
- Agent 调用 MCP 工具时，通过 MCP 协议转发到对应 Server
- 调用结果返回给 Agent，与内置工具体验一致
- 支持超时控制（默认 120 秒）

**Web UI 配置界面：**
- 设置页面增加"MCP 服务器"Tab
- 显示已配置的 Server 列表及连接状态（🟢 已连接 / 🔴 断开）
- 支持添加/编辑/删除 Server 配置
- 支持手动重连按钮

### Out of Scope

- MCP Server 开发（AccoBot 只做客户端）
- MCP Sampling（Server 请求 LLM 补全 — 复杂度高，后续迭代）
- MCP OAuth 认证（先支持 token/env var 方式）
- MCP Resources/Prompts（先只支持 Tools）

## 配置格式

```yaml
# ~/.accobot/config.yaml
mcp_servers:
  # 默认预配置：Playwright 浏览器自动化
  playwright:
    command: "npx"
    args: ["@playwright/mcp@latest"]
    enabled: true
    timeout: 120

  # 用户自行配置示例：金蝶云
  kingdee:
    command: "python"
    args: ["-m", "kingdee_mcp_server"]
    env:
      KINGDEE_URL: "${KINGDEE_URL}"
      KINGDEE_TOKEN: "${KINGDEE_TOKEN}"
    enabled: true
    timeout: 180

  # 远程 HTTP 方式
  invoice_service:
    url: "http://localhost:8080/mcp"
    enabled: true
    timeout: 60
```

## 验收标准

1. **AC-1：配置读取** — Agent 启动时读取 `config.yaml` 的 `mcp_servers` 段，识别所有 `enabled: true` 的 Server 配置
2. **AC-2：Stdio 连接** — 配置了 `command` + `args` 的 Server，启动子进程并通过 stdin/stdout 通信，子进程异常退出时日志记录错误
3. **AC-3：HTTP 连接** — 配置了 `url` 的 Server，通过 HTTP 建立连接
4. **AC-4：工具发现** — 连接成功后，获取 Server 的工具列表，每个工具注册到 AccoBot 的 tool registry，工具名格式为 `mcp_{server}_{tool}`
5. **AC-5：工具调用** — Agent 调用 `mcp_playwright_browser_navigate(url="...")` 时，请求通过 MCP 协议转发到 Playwright Server，结果返回给 Agent
6. **AC-6：超时控制** — 工具调用超过配置的 timeout 秒数后，返回超时错误，不阻塞 Agent
7. **AC-7：连接重试** — Server 连接失败时，自动重试最多 3 次（间隔 2s/4s/8s），全部失败后标记为断开，不影响其他 Server
8. **AC-8：环境变量插值** — 配置中的 `${VAR_NAME}` 在连接时替换为实际环境变量值，变量不存在时报错提示
9. **AC-9：Playwright 默认配置** — 新安装的 AccoBot 默认配置 Playwright MCP Server，用户无需手动配置即可使用浏览器自动化
10. **AC-10：Web UI 状态展示** — 设置页面的 MCP Tab 显示每个 Server 的名称、连接状态、工具数量
11. **AC-11：Agent 无感知** — Agent 调用 MCP 工具与调用内置工具的体验完全一致（同一个 registry、同一个 dispatch 路径）
12. **AC-12：优雅关闭** — AccoBot 退出时，所有 MCP 子进程被正确终止，不留孤儿进程

## 架构设计

```
AccoBot Agent (主线程)
    │
    ├── tool registry (统一注册表)
    │   ├── 内置工具 (query_balance, create_voucher, ...)
    │   └── MCP 工具 (mcp_playwright_xxx, mcp_kingdee_xxx, ...)
    │
    └── MCP Manager (后台线程)
        ├── asyncio 事件循环
        ├── Server "playwright" → stdio 子进程 → 长连接
        ├── Server "kingdee" → stdio 子进程 → 长连接
        └── Server "invoice" → HTTP 连接
```

## 依赖

- REQ-001（Agent 核心框架 — tool registry 接口）
- REQ-011（浏览器自动化 — Playwright 作为默认 MCP Server）
- REQ-016（Skill 系统 — Skill 中引用 MCP 工具名）
- Python `mcp` SDK（pip install mcp）

## 开发节奏（建议分 3 个迭代）

| 迭代 | 内容 | 可独立测试 |
|------|------|-----------|
| 17.1 | 配置读取 + Stdio 连接 + 工具发现注册 | ✅ 用 mock MCP Server 测试 |
| 17.2 | 工具调用 + 超时 + 重试 + 优雅关闭 | ✅ 端到端调用 Playwright |
| 17.3 | HTTP 连接 + Web UI 配置界面 + 环境变量插值 | ✅ 完整功能验收 |

## 开放问题

| # | 问题 | 待定方案 |
|---|------|---------|
| 1 | MCP SDK 版本选择？ | 建议用官方 `mcp` 包最新稳定版 |
| 2 | Playwright MCP 是否替代现有内置 browser 工具？ | 建议共存：内置工具保留作为 fallback，MCP 版本功能更全 |
| 3 | 多个 Server 工具名冲突怎么办？ | 前缀机制天然避免（`mcp_A_tool` vs `mcp_B_tool`） |
| 4 | Server 进程崩溃后是否自动重启？ | 建议不自动重启，记录日志，用户手动重连 |
