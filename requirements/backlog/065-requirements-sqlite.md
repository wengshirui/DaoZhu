# 065 — 需求管理数据化（SQLite 存储）

> 状态: 🆕 待开发
> 优先级: P2
> T-shirt Size: S
> 录入日期: 2026-06-03

---

## 问题陈述

当前 60+ 个需求以 markdown 文件散落在 `requirements/backlog/` 和 `requirements/done/`
目录下。这是项目内部的管理问题：
- 文件越来越多，目录臃肿
- 难以快速查询（"P1 的有哪些？""本月做了几个？""哪些是 M 级？"）
- 无法做开发效率统计（velocity、Size 分布、耗时趋势）
- 每次写 plan.md 都要手动维护两个列表

目标：把需求元数据存入 `requirements/requirements.db`，用 SQLite 做查询和统计的
主数据源。markdown 文件可以逐步不再维护已完成列表（plan.md 的 done 表由 DB 生成）。

**这是项目管理的内部优化，不面向终端用户。**

## 范围

### In Scope

- `requirements/requirements.db`：需求元数据表
- Schema：id, title, status(backlog/in_progress/done/cancelled), priority, size,
  created_at, completed_at, tags, file_path
- 导入脚本：从 plan.md 的已完成列表批量导入历史记录
- plan.md 的已完成列表可以精简为"详见 requirements.db"

### Out of Scope

- 面向终端用户的 API 或前端界面
- 删除已有 markdown 需求文档（md 仍保留详细描述，DB 只存元数据）
- 自动从 md 文件解析 frontmatter 入库（手动导入即可）

## 验收标准

1. **AC1**: `requirements/requirements.db` 存在，包含 `requirements` 表
2. **AC2**: 表中包含所有已完成需求记录（60+ 条，从 plan.md 导入）
3. **AC3**: 可通过 SQL 快速查询，如 `SELECT COUNT(*) FROM requirements WHERE status='done'`
4. **AC4**: plan.md 的已完成列表简化（不再逐条列出，改为引用 DB）

## T-Shirt Size

**S** — 一个建表脚本 + 一次性导入 + plan.md 精简。纯项目内部变更。
