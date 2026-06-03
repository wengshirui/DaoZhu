# 065 — 需求管理数据化（SQLite 存储）

> 状态: 🆕 待开发
> 优先级: P2
> T-shirt Size: S
> 录入日期: 2026-06-03

---

## 问题陈述

当前已完成的 60+ 个需求以 markdown 文件形式散落在 `requirements/backlog/` 和
`requirements/done/` 目录下。随着需求持续增长：
- 文件越来越多，目录臃肿
- 难以快速查询（"哪些是 P1？""哪些涉及 Agent？"）
- 无法做统计分析（完成速度、Size 分布、耗时趋势）
- AI 复盘时读不到结构化的需求历史

应该把需求元数据存入 SQLite，方便查询和分析，markdown 文件可以仍然保留（给人读），
但 SQLite 是查询和统计的主数据源。

## 用户故事

**As a** 岛主开发者
**I want** 所有需求信息结构化存入 SQLite
**So that** 我可以快速查询、统计分析需求历史，AI 也能方便读取

## 范围

### In Scope

- 在 `requirements/` 目录下新建 `requirements.db`
- Schema：id, title, status, priority, size, created_at, completed_at, tags, description
- 从现有 plan.md 的已完成列表批量导入历史数据
- 新增需求时同时写入 SQLite（backlog md 文件仍可选保留）
- 提供 CLI 或 API 查询接口（"列出所有 P1 需求"、"本月完成了几个"）

### Out of Scope

- 删除现有 markdown 文件（保留给人读）
- 前端需求管理界面（后续可做）
- 需求间的依赖关系图

## 验收标准

1. **AC1**: `requirements/requirements.db` 存在，包含 `requirements` 表
2. **AC2**: 表中包含所有已完成需求的元数据（从 plan.md 导入的 60+ 条）
3. **AC3**: 新创建需求时自动写入 SQLite（add_requirement 函数）
4. **AC4**: 可通过 SQL 查询统计（如 `SELECT COUNT(*) FROM requirements WHERE status='done'`）
5. **AC5**: AI 的 `_build_stats_context()` 可以读取需求统计（如"本周完成 3 个需求"）

## 业务价值

- 需求检索从"翻文件"变为"查数据库"（效率提升 10x）
- 为 AI 复盘（#062）提供结构化数据源
- 为后续的效率分析（velocity、burndown）打基础
- 目录更干净（已完成的需求不用塞满 done/ 文件夹）

## T-Shirt Size

**S** — 建表 + 导入脚本 + 一个 helper 函数；无前端改动，无复杂逻辑

## 依赖

- 现有 plan.md（作为导入数据源）
- config.py 中的 PLATFORM_ROOT（确定 db 路径）
