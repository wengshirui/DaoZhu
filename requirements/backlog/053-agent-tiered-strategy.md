# 053 — Agent 分层解决策略

> 状态: 🆕 待开发
> 优先级: P1
> T-shirt Size: M — 改造 Agent 核心循环 + 用户确认交互 + Playwright 集成限制；风险在于循环控制和 token 计费准确性
> 录入日期: 2026-05-29

---

## 问题陈述

当前 Agent 处理问题时策略单一，没有明确的"升级"机制。用户希望 Agent 能分层递进：先用本地能力解决，搞不定再联网，还搞不定就死磕——但每次升级都需要用户明确同意，并对资源消耗有清晰预期。

## 范围

**In Scope:**
- 三级递进策略：本地 → 联网（受限）→ 无限循环（死磕）
- Level 2 联网限制：工具调用 ≤ 5 次，上下文 ≤ 8K tokens
- Level 3 安全阀：token 上限（100K tokens）或金额上限（¥5）
- 用户同意机制：对话中询问，用户回复确认
- Token 消耗实时提示（Level 3）

**Out of Scope:**
- 自动判断何时"本地搞不定"（初期由 Agent 自行判断，后续可优化）
- 多模型切换策略（已有 045）

---

## User Story

> As a 岛主用户，I want Agent 在解决问题时能逐步升级策略（本地→联网→死磕），每次升级前征求我的同意并告知消耗预期，so that 我既能高效解决问题，又不会被意外的 token 消耗吓到。

---

## 验收标准

1. Agent 默认使用 Level 1（本地工具、技能、工作区数据）尝试解决问题
2. 当 Agent 判断本地无法解决时，在对话中提示用户："本地资源无法解决，是否允许我联网搜索？（将使用 Playwright，限制 5 次工具调用）"
3. 用户回复同意后，Agent 进入 Level 2，使用 Playwright 联网，工具调用 ≤ 5 次
4. Level 2 超出限制仍未解决时，提示用户："联网也未能解决，是否进入深度模式？（不限次数，预计消耗 XX tokens，约 ¥X.XX）"
5. 用户同意后进入 Level 3，每 10 次迭代显示当前累计消耗
6. Level 3 达到安全阀（100K tokens 或 ¥5）时自动暂停，询问是否继续
7. 用户可随时输入"停止"中断任何级别的执行
8. 对话历史中清晰标记当前执行级别（Level 1/2/3）

---

## 技术方案

### Agent 循环改造（agent.py）

```python
class SolveLevel(Enum):
    LOCAL = 1       # 本地工具+技能
    ONLINE = 2      # Playwright 联网（受限）
    UNLIMITED = 3   # 无限循环（死磕）

# 在 agent 循环中增加级别控制
self.current_level = SolveLevel.LOCAL
self.level2_tool_count = 0
self.level3_token_total = 0
```

### 用户确认机制

- 复用现有 SSE 流式对话，Agent 发送特殊消息类型 `level_upgrade_request`
- 前端渲染为确认按钮（同意/拒绝）
- 用户也可直接文字回复"同意""继续""停止"

### Token 计费

- 利用现有 tool_logs 表记录每次调用的 token 消耗
- Level 3 实时累加，每 10 次迭代汇报

---

## 依赖

- 现有 Playwright MCP 工具（039 已完成）
- 现有工具调用日志系统（050 已完成）
- Agent 核心循环（agent.py）
