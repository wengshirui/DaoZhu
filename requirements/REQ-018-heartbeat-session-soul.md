# REQ-018 主动循环 / Session 压缩 / 身份文件化

**状态：** 📝 Draft  
**优先级：** P1（用户体验 + 系统稳定性）  
**T-Shirt Size：** M - 三个独立子功能，各自复杂度低但合在一起有一定工作量

---

## 问题陈述

1. **主动循环缺失** — AccoBot 只能被动响应用户消息，无法主动提醒报税截止、对账异常等时间敏感事项
2. **长对话爆 token** — 复杂操作（如 Playwright 多步骤）会累积大量消息历史，超出模型 context window 导致报错或截断
3. **Agent 行为硬编码** — system prompt 写死在代码里，用户无法自定义 Agent 的性格、专业偏好和行为规则

## 用户故事

**Story A：** As a 代账会计，I want AccoBot 在报税截止前主动提醒我，so that 我不会忘记申报导致罚款

**Story B：** As a 用户，I want 长时间对话不会因为消息太多而出错，so that 复杂操作（如 Playwright 多步骤）能顺利完成

**Story C：** As a 用户，I want 通过编辑一个文件来自定义 Agent 的行为风格，so that Agent 能按我的习惯和偏好工作

## 范围

### In Scope

**A. Heartbeat 主动循环：**
- 后台定时检查（默认每 5 分钟）
- 检查报税日历，截止前 N 天通过 Web UI 推送提醒
- 检查待办事项状态变化
- 可配置开关和间隔

**B. Session 压缩：**
- 当消息历史超过 token 阈值时自动压缩
- 压缩策略：保留最近 N 条 + 摘要旧消息
- 关键事实提取到记忆系统
- 压缩对用户透明（不影响对话体验）

**C. SOUL.md 身份文件：**
- `~/.accobot/SOUL.md` 定义 Agent 人格和行为规则
- 内容注入 system prompt（优先级高于默认 prompt）
- 提供默认模板
- Agent 可通过工具读取和建议修改

### Out of Scope

- 跨平台推送（消息平台推送在 REQ-013）
- 向量化记忆搜索（后续迭代）
- 多 Agent 协作

## 验收标准

### A. Heartbeat 主动循环

1. **AC-A1：定时检查** — Web UI 启动后，后台每 5 分钟（可配置）执行一次检查循环
2. **AC-A2：报税提醒** — 报税截止前 5 天，Web UI 待办区域自动出现提醒（无需用户主动刷新）
3. **AC-A3：可配置** — config.yaml 中 `heartbeat.enabled` 和 `heartbeat.interval_minutes` 可控制开关和频率
4. **AC-A4：不阻塞** — Heartbeat 在后台线程运行，不影响正常对话响应速度

### B. Session 压缩

5. **AC-B1：自动触发** — 当消息历史估算超过 8000 token 时，自动压缩旧消息
6. **AC-B2：保留近期** — 压缩后保留最近 10 条消息原文 + 旧消息的摘要
7. **AC-B3：透明压缩** — 用户不会看到"消息被删除"的提示，对话体验连续
8. **AC-B4：事实保留** — 压缩时提取关键事实（如"用户公司是餐饮行业"）存入记忆

### C. SOUL.md 身份文件

9. **AC-C1：文件加载** — Agent 启动时读取 `~/.accobot/SOUL.md`，内容注入 system prompt
10. **AC-C2：默认模板** — 首次启动时自动生成默认 SOUL.md 模板（包含角色、风格、规则示例）
11. **AC-C3：热更新** — 修改 SOUL.md 后，下次新建对话时生效（不需要重启服务）
12. **AC-C4：优先级** — SOUL.md 内容追加在默认 system prompt 之后，可覆盖默认行为

## 依赖

- REQ-001（Agent 核心框架 — system prompt 注入）
- REQ-006（报税日历 — Heartbeat 检查数据源）
- REQ-012（记忆系统 — 压缩时存储关键事实）

## 开发节奏

| 迭代 | 内容 | 可独立测试 |
|------|------|-----------|
| 18.1 | SOUL.md 身份文件（最简单，无依赖） | ✅ |
| 18.2 | Session 压缩（Agent 内部改造） | ✅ |
| 18.3 | Heartbeat 主动循环（后台线程 + WebSocket 推送） | ✅ |
