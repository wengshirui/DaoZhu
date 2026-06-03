# 岛主 DaoZhu — 需求计划

> 最后更新: 2026-06-03

---

## 需求管理规范

### 文件结构

```
requirements/
├── plan.md            # 本文件 — 需求总览（只列 backlog + 进行中）
├── requirements.db    # 全量需求元数据（SQLite，查询/统计用）
├── init_db.py         # DB 初始化 + 导入脚本
├── AGENTS.md          # AI 需求管理指南
├── backlog/           # 待开发需求（详细文档）
├── references/        # 技术参考文档
└── done/              # 已完成需求（归档，详细描述保留）
```

### 状态流转

`backlog` → `in_progress` → `done`（或 `cancelled`）

### 查询已完成需求

```sql
-- 连接: requirements/requirements.db
SELECT id, title FROM requirements WHERE status = 'done' ORDER BY id;
-- 共 54 条已完成需求
```

---

## 进行中

（无）

---

## 待开发（backlog/）

| 优先级 | ID | 需求 | Size | 备注 |
|--------|-----|------|------|------|
| P0 | 046 | 火柴人剧场 BGM + 配音 | M | |
| P1 | 061 | 对话 Token 消耗 + 速度显示 | S | |
| P1 | 062 | AI 定时自我复盘（记忆 + 日志） | M | |
| P1 | 063 | 智能模型路由（大模型带小模型） | M | |
| P1 | 064 | AI 主动交互（评估需求 + 主动提问） | M | |
| P1 | 066 | Gitee 生态架构（四仓库体系） | L | 含原 #043 #009 |
| P2 | 020 | 本地性能检测 + 智能推荐 | S | |
| P3 | 055 | 待办今日聚焦桌面侧边栏 | M | |

---

## 已取消

| ID | 需求 | 原因 |
|----|------|------|
| 019 | 孕期管理 + 学习辅助 | 需求不明确 |
