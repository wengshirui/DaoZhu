# REQ-037: 配置统一存储到 SQLite

> Intake ID: 2026-05-26-config-db
> 优先级: 🔴 高（架构优化，解决路径依赖问题）

---

## 问题陈述

当前配置分散在 config.json + .env 文件中，工作区读取 .env 依赖相对路径计算（`Path(__file__).parent.parent.parent`），容易出错。需要统一存储到 SQLite，工作区需要时从平台 API 获取或本地复制一份 config.db。

## 方案

- 项目根目录：`config.db`（平台级配置，含 API Key、Token 等）
- 工作区目录：`config.db`（工作区级配置，由平台同步或工作区自行管理）
- 工作区读取配置时，优先读本地 config.db，没有则通过平台 API 获取

## 验收标准

| # | AC | 可测试性 |
|---|-----|----------|
| 1 | 平台启动时从 .env 迁移配置到 config.db | 启动后检查 db |
| 2 | 工作区通过 API `GET /api/config/{key}` 获取平台配置 | 工作区内调用验证 |
| 3 | 设置页面修改配置写入 config.db 而非 .env | 修改后检查 db |
| 4 | 向后兼容：.env 仍可用，优先级低于 config.db | 两者都有时验证 |

## T-Shirt Size

**M (5 pts)** — 涉及 config.py 重构 + 迁移逻辑 + API 改造 + 工作区适配

---
