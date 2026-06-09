# 079 — Agent 架构重设计

> 状态: 📋 设计中
> 优先级: P0
> T-shirt Size: XL
> 录入日期: 2026-06-08

---

## 问题陈述

当前 agent 架构存在根本性设计问题，导致：
1. **幻觉无法根治** — 一个 LLM 同时做规划+执行+回复，混淆执行结果和想象
2. **agent.py 持续膨胀** — 每解决一个问题就往里塞规则/context，已经难以维护
3. **prompt 规则互相稀释** — 诚实原则跟风格规则跟 API hint 混在一起，权重分散
4. **质检是让 AI 审查自己** — fox guarding the henhouse，本质上不可靠

## 行业最佳实践对比

### 1. Plan & Execute 分离（Oracle OIC、Karpathy "LLM as Compiler"）

> "The Planner thinks without acting. The Executor acts without thinking. Together, they separate strategy from execution."

核心思想：
- **Planner Agent** — 只做意图识别和步骤规划，不调工具
- **Executor Agent** — 按计划执行工具调用，不做创造性回答
- **分离的价值：** 规划时不会编造执行结果，执行时不会偏离计划

### 2. OpenAI Agents SDK 架构

```
Agent Definition (instructions + tools + handoffs)
    ↓
Runner (执行循环)
    ├── LLM Call → Tool invocation → Result processing → 循环
    ├── Guardrails (并行验证：input + output)
    ├── Handoffs (任务委派给专业子 Agent)
    └── Tracing (全链路可观测)
```

关键设计：
- **Guardrails 与执行并行运行** — 不是事后检查，是实时拦截
- **Output Guardrail** — 在最终输出前检查回复是否合规
- **结构化输出** — `output_type` 强制 Agent 返回 schema 匹配的结构

### 3. hermes-agent 架构

```
System Prompt (三层: stable / context / volatile)
    ↓
Conversation Loop (run_conversation)
    ├── Tool Call → handle_function_call → result
    ├── Tool Guardrail Controller (循环检测 + 阻断)
    ├── File Mutation Verifier (后置代码级验证)
    └── Turn Completion Explainer (异常退出解释)
```

关键设计：
- **后置验证器是代码级的** — 不信任模型，直接追加事实
- **模型行为引导按家族定制** — GPT/Gemini/DeepSeek 各有专属规则
- **Guardrail 是独立模块** — 纯函数，无副作用，易测试

### 4. Anthropic 防幻觉指南

> "Claude produces a plausible-looking implementation that doesn't handle edge cases. Fix: Always provide verification. If you can't verify it, don't ship it."

核心原则：
- 给 AI 提供验证工具（让它可以自查）
- 结构化 tool 描述（精确到参数级别）
- Citation 机制（要求引用来源）

### 5. RP-ReAct（多 Agent 企业自动化）

> "Decouples high-level planning (RPA) from low-level execution (PEA). Utilizes a context-saving mechanism that limits LLM token usage by offloading extensive tool outputs."

关键：**工具输出不全量回传给 LLM**，只传摘要。避免 context 膨胀导致注意力稀释。

---

## 岛主当前架构 vs 目标架构

### 当前（单体 Agent）

```
用户消息
    ↓
agent_chat_stream() — 一个函数干所有事：
    [system prompt (规则堆叠)]
    + [context (API hint + 记忆 + 统计 + 工作区列表)]
    + [对话历史]
    → LLM 同时做：判断意图 + 调工具 + 处理结果 + 生成回复
    → 质检（让同一个 LLM 再审一遍自己的回复）
    ↓
用户看到回复
```

**问题：一个 LLM 角色切换太频繁，context 过载，幻觉不可避免。**

### 目标（Pipeline Agent）

```
用户消息
    ↓
[Stage 1: 路由 / 意图识别]  ← 轻量，可能不需要 LLM
    判断：纯聊天 / 需要查数据 / 需要执行操作 / 需要创建东西
    输出：结构化意图 + 需要的工具列表
    ↓
[Stage 2: 执行]  ← 工具循环，有 Guardrail
    按意图调用工具，收集结构化结果
    Guardrail: 循环检测、失败重试上限、权限拒绝
    输出：ExecutionRecord { tool_calls: [...], results: [...], errors: [...] }
    不生成自然语言，只产出数据
    ↓
[Stage 3: 输出生成]  ← 独立 LLM 调用
    输入：用户原始问题 + ExecutionRecord（结构化）
    职责：把执行结果翻译成自然语言
    约束：只能引用 ExecutionRecord 中的数据，不能添加未验证的信息
    ↓
[Stage 4: 后置验证]  ← 代码级，不用 LLM
    比对：输出文本 vs ExecutionRecord
    检查：输出中的数字是否来自 results？声称"已完成"的操作是否在 tool_calls 中成功？
    追加：如有矛盾 → 追加 ⚠️ 警告
    ↓
用户看到回复
```

---

## 每个 Stage 的详细设计

### Stage 1: 路由 / 意图识别

| 输入 | 输出 | 是否需要 LLM |
|------|------|-------------|
| 用户消息 + profile | `Intent` 结构体 | 简单意图不需要（规则匹配），复杂意图需要 |

```python
@dataclass
class Intent:
    type: str  # "query" | "action" | "chat" | "create"
    workspace: str | None  # 目标工作区
    tools_needed: list[str]  # 需要调用的工具
    params: dict  # 解析出的参数
```

**规则路由（不花 token）：**
- "今天天气" → `Intent(type="query", tools_needed=["web_search"])`
- "我有几个待办" → `Intent(type="query", workspace="todo", tools_needed=["call_workspace_api"], params={"path": "/tasks"})`
- "帮我创建一个记账工作区" → `Intent(type="create")`

**LLM 路由（复杂/模糊意图）：**
- "把那个文件里的东西整理一下" → 需要 LLM 理解上下文

### Stage 2: 执行

```python
@dataclass
class ExecutionRecord:
    tool_calls: list[ToolCall]  # 每次调用的工具名+参数
    results: list[ToolResult]  # 每次的返回值（成功/失败）
    errors: list[str]  # 失败原因列表
    duration_ms: int  # 总耗时
```

**关键原则：这一步不生成任何给用户看的文本。** 只产出结构化数据。

**Guardrail（独立模块）：**
- 同一工具同参数连续失败 2 次 → 停止重试
- 循环检测（输出不变）→ 中断
- 权限拒绝 → 记录到 errors

### Stage 3: 输出生成

**System Prompt（极简，只做一件事）：**
```
你是输出翻译器。把下面的执行结果翻译成自然语言回复给用户。
规则：只能引用 ExecutionRecord 中的数据，不能添加任何未出现的信息。
如果执行失败了，直接说"XX 操作失败了：原因"。
```

**为什么这能解决幻觉：** 这个 LLM 看不到工具调用的中间过程，只看到最终的结构化结果。它没有"可以编造的素材"——要么照着数据说，要么说没有数据。

### Stage 4: 后置验证

**纯代码，不用 LLM：**
```python
def verify_output(text: str, record: ExecutionRecord) -> str | None:
    """返回警告文本，或 None 表示通过"""
    warnings = []
    
    # 检查：声称有数字但执行记录中没有对应数据
    numbers_in_text = extract_numbers(text)
    numbers_in_results = extract_numbers_from_results(record.results)
    for n in numbers_in_text:
        if n not in numbers_in_results and n > 1:
            warnings.append(f"⚠️ 文中提到的数字 {n} 未在工具返回中找到")
    
    # 检查：声称"已完成"但工具有失败
    if record.errors and ("完成" in text or "成功" in text):
        warnings.append(f"⚠️ 有 {len(record.errors)} 个操作失败，请确认实际状态")
    
    return "\n".join(warnings) if warnings else None
```

---

## 实施策略

### Phase 1: 拆分输出层（最小改动，验证效果）

只改 Stage 3 — 把"翻译执行结果为自然语言"独立出来：
- 工具循环结束后，不让同一个 LLM 直接回复
- 新起一个 LLM 调用，只给它执行结果 + 用户问题
- 验证：幻觉是否减少

### Phase 2: 加入后置验证

把当前的质检改为代码级 verify_output：
- 不再让 LLM 质检自己
- 代码比对数字和状态
- 有矛盾时追加警告

### Phase 3: 路由层独立

简单意图用规则匹配（零 token），复杂意图用 LLM：
- 减少不必要的 LLM 调用
- 明确告诉执行层"你要调什么工具"

### Phase 4: 完整 Pipeline

全部阶段独立运行，可单独测试和优化。

---

## 文件结构规划

```
daozhu/
├── agent.py              → 改为 pipeline 编排入口（瘦）
├── agent_router.py       → Stage 1: 意图识别 + 路由
├── agent_executor.py     → Stage 2: 工具执行循环
├── agent_responder.py    → Stage 3: 输出生成
├── agent_verifier.py     → Stage 4: 后置验证
├── agent_protocol.py     → 协议转换（已有）
├── agent_guardrails.py   → Guardrail 控制器（参考 hermes-agent）
├── prompts.py            → 各阶段 prompt 集中管理（已有）
└── models.py             → 数据结构定义（Intent, ExecutionRecord 等）
```

---

## 与 078 的关系

078（后置验证器）是本需求 Stage 4 的子集。如果 079 落地，078 自然包含在内，不需要单独做。

---

## 风险

1. **改动大** — 影响核心对话流程，需要充分测试
2. **分阶段 LLM 调用增加延迟** — 每次回复从 1 次 LLM 变为 2 次（执行+输出）
3. **简单对话过度设计** — 纯聊天不需要 pipeline，需要快速路径

**缓解：**
- Phase 1 只改输出层，风险最小
- 路由层识别"纯聊天"直接跳过 pipeline，走快速路径
- 延迟增加约 1-2 秒，换取准确性提升

---

## 参考来源

| 来源 | 关键设计 | 适用于岛主 |
|------|---------|-----------|
| Oracle OIC Plan & Execute | Planner 不调工具，Executor 不即兴 | Stage 1+2 分离 |
| OpenAI Agents SDK | Guardrails 并行 + output_type 结构化 | Stage 4 验证 |
| hermes-agent | 文件变异验证器（代码级后置）| Stage 4 后置 |
| Anthropic 防幻觉 | "If you can't verify it, don't ship it" | 设计原则 |
| RP-ReAct | 工具输出只传摘要，不全量回传 | Stage 3 只看摘要 |
| Karpathy "LLM as Compiler" | LLM 产出结构化 artifact，runtime 执行 | Stage 2 结构化输出 |
