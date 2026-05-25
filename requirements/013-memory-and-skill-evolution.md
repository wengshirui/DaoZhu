# REQ-013: 对话记忆与 Skill 自动优化

> Intake ID: 2025-05-25-memory-skill-evolution

---

## 研究参考

| 项目 | Stars | 记忆方案 | Skill 优化方案 |
|------|-------|----------|---------------|
| Hermes-Agent | — | SQLite FTS5 会话搜索 + 分层记忆（笔记/检索/程序性） | Curator 系统：追踪使用频率，自动归档过期 skill |
| OpenClaw | — | Markdown 文件 + 向量嵌入 + 每日日志 + auto-dream 整合 | 版本化 SKILL.md + A/B 测试 + 自我改进循环 |

---

## 岛主适配方案

### 记忆系统（三层）

```
┌─────────────────────────────────────────┐
│ Layer 1: 会话记忆（短期）               │
│ - 当前对话的消息历史                     │
│ - 存储在 chat.db messages 表            │
│ - 上下文窗口内直接传给 LLM              │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ Layer 2: 用户画像（中期）               │
│ - 用户偏好、常用工作区、习惯            │
│ - 从对话中自动提取                       │
│ - 存储在 memory.db user_profile 表      │
│ - 每次对话开始时注入 system prompt      │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ Layer 3: 知识库（长期）                 │
│ - 历史对话摘要                           │
│ - 工作区创建经验                         │
│ - 用户反馈和修正                         │
│ - 存储在 memory.db knowledge 表         │
│ - 通过关键词/语义搜索检索               │
└─────────────────────────────────────────┘
```

### Skill 自动优化

```
用户使用 skill 完成任务
         │
         ▼
┌─────────────────────────┐
│ 记录使用数据             │
│ - 哪个 skill 被调用     │
│ - 成功/失败             │
│ - 用户满意度（隐式）    │
└────────┬────────────────┘
         │
         ▼ (后台定期)
┌─────────────────────────┐
│ Skill 评估              │
│ - 使用频率              │
│ - 成功率                │
│ - 最后使用时间          │
└────────┬────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
 高频成功   低频/失败
    │         │
    ▼         ▼
 保持/优化  建议改进/归档
```

---

## 提炼后的需求

### 问题陈述

当前管家没有记忆能力，每次对话都是全新开始。用户重复描述偏好、管家重复犯同样的错误。Skill 也是静态的，不会根据使用反馈自我改进。

### 范围

**包含（In Scope）：**

- Layer 1: 会话历史上下文（已有，优化截断策略）
- Layer 2: 用户画像自动提取与注入
- Layer 3: 知识库存储与检索（关键词搜索，不做向量）
- Skill 使用追踪（调用次数、成功率、最后使用时间）
- Skill 自动建议优化（基于使用数据）

**不包含（Out of Scope）：**

- 向量嵌入/语义搜索（MVP 阶段用关键词 FTS5 足够）
- 多用户隔离（单用户本地平台）
- Auto-dream 记忆整合（后续迭代）

### 用户故事

**Story 1**: As a 用户，I want 管家记住我的偏好（如"我喜欢暗色主题"），so that 不需要每次重复说明。

**Story 2**: As a 用户，I want 管家能回忆之前的对话内容（如"上次帮我建的那个工作区"），so that 对话有连续性。

**Story 3**: As a 平台，I want 追踪 skill 使用数据，so that 能识别哪些 skill 需要优化或归档。

### 验收标准

| # | 验收标准 | 可测试性 |
|---|----------|----------|
| AC-1 | 用户说"我喜欢暗色主题"后，后续新对话中管家自动知道这个偏好 | 新会话中问"我喜欢什么主题"能正确回答 |
| AC-2 | 用户说"上次帮我建的那个待办工作区怎么样了"，管家能检索到相关历史 | 返回包含待办工作区创建记录的回答 |
| AC-3 | 每次 skill 被调用时，记录调用时间、是否成功、耗时 | 查询 skill_usage 表有对应记录 |
| AC-4 | 超过 30 天未使用的 skill 被标记为 stale | 定期检查后 stale 标记正确 |
| AC-5 | 会话历史超过 token 限制时，自动截断旧消息但保留摘要 | 长对话不报 token 超限错误 |

---

## 技术设计（草案）

### memory.db Schema

```sql
-- 用户画像
CREATE TABLE user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    source TEXT DEFAULT 'auto',
    confidence REAL DEFAULT 0.8,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 知识条目
CREATE TABLE knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT,
    source_conversation_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Skill 使用记录
CREATE TABLE skill_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id TEXT NOT NULL,
    action TEXT NOT NULL,
    success INTEGER DEFAULT 1,
    duration_ms INTEGER,
    context TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- FTS5 全文搜索
CREATE VIRTUAL TABLE knowledge_fts USING fts5(
    title, content, keywords,
    content=knowledge, content_rowid=id
);
```

### 记忆注入流程

```
用户发送消息
     │
     ▼
┌──────────────────┐
│ 1. 加载用户画像   │ → 注入 system prompt
│ 2. 搜索相关知识   │ → 注入 context
│ 3. 加载会话历史   │ → messages 列表
└──────────────────┘
     │
     ▼
  调用 LLM
     │
     ▼
┌──────────────────┐
│ 4. 分析回复       │
│ 5. 提取新偏好     │ → 更新 user_profile
│ 6. 提取新知识     │ → 写入 knowledge
└──────────────────┘
```

---

## T-Shirt Size

**L (8 pts)** — 涉及记忆提取/注入/检索、skill 追踪、后台任务，跨多个模块。

---

## 依赖

| 依赖 | 说明 |
|------|------|
| 007 AI 对话后端 | ✅ 已完成，在此基础上扩展 |
| 005 平台全局配置 | ✅ 已完成 |

---

## 状态

- [x] 需求录入
- [x] 研究参考（Hermes + OpenClaw）
- [x] 需求提炼
- [ ] 移交开发
