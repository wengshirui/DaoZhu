# 需求管理 AI 指南

> 给 AI 编码助手的指南。管理岛主项目需求时遵循以下规则。

---

## 数据源

| 文件 | 用途 | 何时读 |
|------|------|--------|
| `requirements.db` | 全量需求元数据 + 已完成需求完整内容 | 查询/统计/归档检索 |
| `plan.md` | 当前 backlog 概览 | 了解待做优先级 |
| `backlog/*.md` | **待开发**需求详细文档 | 开发具体需求时 |
| `references/*.md` | 开源项目学习笔记 | 需要技术参考时 |

### 存储策略

- **待开发（backlog）** → 用 md 文件存（方便阅读和修改）
- **已完成（done）** → 完整内容归档到 `requirements.db` 的 `description` 字段
- 需求完成后：把 md 内容写入 DB → 删除 backlog 中的 md 文件

---

## 需求生命周期

```
录入 → backlog → in_progress → done
                             → cancelled
```

### 录入新需求

1. 分配下一个可用 ID（查 DB: `SELECT MAX(id) FROM requirements`）
2. 创建 `backlog/{ID}-{slug}.md`（含 AC + Size + 依赖）
3. 写入 DB: `INSERT INTO requirements (id, title, status, priority, size) VALUES (...)`
4. 更新 `plan.md` 的 backlog 表

### 开始开发

1. DB: `UPDATE requirements SET status='in_progress' WHERE id=?`
2. plan.md: 从 backlog 表移到"进行中"

### 完成需求

1. DB: `UPDATE requirements SET status='done', completed_at=date('now'), description='完整md内容' WHERE id=?`
2. plan.md: 从"进行中"移除（已完成的不再列出，查 DB 即可）
3. backlog/*.md 可删除（内容已归档到 DB 的 description 字段）

### 取消需求

1. DB: `UPDATE requirements SET status='cancelled' WHERE id=?`
2. plan.md: 加到"已取消"表并注明原因

---

## 需求文档模板

```markdown
# {ID} — {标题}

> 状态: 🆕 待开发
> 优先级: P1
> T-shirt Size: M
> 录入日期: YYYY-MM-DD

---

## 问题陈述
（1-2 段描述为什么要做这个）

## 用户故事
As a [角色], I want [目标], so that [价值]

## 范围
### In Scope
- ...
### Out of Scope
- ...

## 验收标准
1. **AC1**: （可测试的具体条件）
2. **AC2**: ...
3. **AC3**: ...

## T-Shirt Size
**{Size}** — {复杂度原因}; {风险因素}

## 依赖
- #XXX（依赖什么）
```

---

## 开发流程

### 分诊路由

| Size | 路由 |
|------|------|
| XS/S 无依赖 | 直接实现 |
| S + 有依赖 | 先写简单 spec 再实现 |
| M/L/XL | 拆分 user story → 逐个实现 |

### 有依赖的判定

以下任一为真即"有依赖"：
- 跨前后端
- 涉及 schema 变更
- 集成第三方服务
- 依赖其他未完成需求

### 实现规范

1. 确认 AC 清晰 → 如果不清楚，先问 PO
2. 实现代码 → 遵循 AGENTS.md（项目根目录）的编码规范
3. 验证 → 确保能导入/启动无报错
4. 提交 → 一个 commit 说清做了什么
5. 更新状态 → DB + plan.md

### commit message 规范

```
feat: #{ID} {简述}        — 新功能
fix: #{ID} {简述}         — 修 bug
docs: {简述}              — 文档变更
chore: {简述}             — 内部优化/清理
```

---

## 查询快捷 SQL

```sql
-- 当前 backlog（按优先级排序）
SELECT id, title, priority, size FROM requirements
WHERE status = 'backlog' ORDER BY priority, id;

-- 本周完成
SELECT id, title, completed_at FROM requirements
WHERE status = 'done' AND completed_at >= date('now', '-7 days');

-- Size 分布
SELECT size, COUNT(*) FROM requirements GROUP BY size;

-- 下一个可用 ID
SELECT MAX(id) + 1 AS next_id FROM requirements;
```

---

## 优先级定义

| 优先级 | 含义 | 排期 |
|--------|------|------|
| P0 | 阻塞性 / 核心体验 | 本周内 |
| P1 | 重要提升 | 2 周内 |
| P2 | 有价值但不紧急 | 排期时做 |
| P3 | 锦上添花 | 空闲时做 |

---

## Size 与工期预估

| Size | 点数 | 预估工期 |
|------|------|---------|
| XS | 1-2 | 半天 |
| S | 3 | 1 天 |
| M | 5 | 2-3 天 |
| L | 8 | 1 周 |
| XL | 13+ | 2+ 周 |
