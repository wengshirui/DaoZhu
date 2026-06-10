# 080 — Agent 思维重塑 Phase 1：意图识别 + 规划

> 状态: 📋 待开发
> 优先级: P0
> T-shirt Size: M
> 录入日期: 2026-06-09
> 拆分说明: 原 XL 需求拆为 080（意图+规划）+ 081（执行+验证）

---

## Phase 1 范围：意图识别 + 规划

本阶段只做**执行前**的部分——让 agent 先想清楚再动手。
执行阶段（目标驱动循环 + 验证 + 补充执行）放到 #081。

---

## 问题陈述

当前 agent 有两个根本问题：

### 问题 1：服务员模式（听到就答）

听到问题就冲去调工具快速回答。这导致：
1. **不理解用户真正要什么**：用户说"看看待办"，agent 直接调 API 全量返回，而不是问"你是想看今天的？高优的？还是某个项目的？"
2. **不规划就行动**：有时候乱调工具（read_file 读 .db 文件），有时候不调工具就编答案
3. **不验证就交付**：工具返回后直接输出，不检查数据是否完整、是否回答了用户的问题
4. **不考虑呈现方式**：同样的数据，面对 PM 和面对开发应该有不同的组织方式

### 问题 2：问答导向（目标是"回复"而不是"解决"）

agent 的目标被定义为"给用户一个文字回复"，而不是"把问题解决掉"。这导致：
1. **遇到不知道的就编** — "现在几点"→ 编一个时间，而不是想到"我有 terminal 工具可以跑脚本获取真实时间"
2. **给建议而不动手** — "帮我整理文件"→ 说"你可以这样做…"，而不是直接动手整理
3. **缺乏解决问题的创造力** — 当直接路径走不通时不会想替代方案。比如没有"获取时间"工具，不代表不能通过 terminal/脚本/API 间接获取
4. **把"说了"当"做了"** — agent 觉得输出一段文字就完事了，实际上问题根本没解决

**根因 1：agent 的循环只有"调工具→回答"，缺少"思考"和"验证"环节。**
**根因 2：agent 的目标函数错了——不是"生成回复"，是"解决问题"。文字只是告知结果的形式。**

---

## 行业对比

### Kiro（Spec-Driven Development）

> "Instead of jumping straight to code, it starts with a spec — requirements, design, and a task breakdown."

Kiro 的核心：**先理解意图，写成结构化规格，然后才执行。**
- 用户说"加一个功能" → Kiro 不会直接写代码
- 而是先输出：Requirements → Design → Task List → 然后逐步执行

### Codex（Task-Oriented Agent）

> "scans through your codebase for relevant files, reads them to build context, makes edits, and runs tests to verify the fix worked."

Codex 的核心：**执行后必须验证。声称"做完了"之前先跑测试。**
- 不是"我改了文件所以完成了"
- 而是"我改了文件 → 跑测试 → 测试通过 → 才说完成"

### Claude Code（PLAN→REVIEW→EXECUTE→VERIFY→COMMIT）

> "Enforces running verification commands like tests, linters, and builds, then confirming outputs before claiming completion."

Claude Code 的核心：**5 步流程，每步有检查点。**
- PLAN: 确定做什么、怎么做
- REVIEW: 检查计划合理性
- EXECUTE: 执行操作
- VERIFY: 验证结果正确
- COMMIT: 确认交付

### 共同点：目标是"解决"不是"回答"

这些产品都不是"听到问题就回答"。它们的 agent：
1. **先确认理解对了**（不急着行动）
2. **有明确的执行计划**（不是随机调工具）
3. **执行后验证结果**（不是调完就算完）
4. **目标是把事做成** — Codex 跑测试、Claude Code commit 代码、Kiro 写出 spec。它们的输出不是一段话，是一个被解决的问题
5. **有创造力** — 一条路走不通会想替代方案（Hermes 有 terminal 后备、delegate_task 分发子任务）

---

## 岛主当前 vs 目标

### 当前（问答机器）

```
用户消息 → LLM 决定调哪个工具 → 调工具 → 把结果翻译成自然语言 → 输出文字
```

问题：
- 目标是"输出文字回复"，不是"解决问题"
- LLM "决定调哪个工具" 时经常判断错误（编造答案 / 选错工具 / 参数不对）
- 走不通时不会想替代方案（没有"获取时间"工具 → 直接编，而不是想到跑脚本）
- 没有"理解用户真正要什么"的环节
- 没有"验证结果是否回答了问题"的环节

### 目标（解决问题的管家）

核心转变：**agent 的目标不是"生成回复"，是"把问题解决掉"。文字只是告知结果的形式。**

```
用户消息
    ↓
[1. 理解] — 用户的问题是什么？"解决"意味着什么？需要追问吗？
    ↓
[2. 规划] — 要解决这个问题，需要哪几步？有哪些可用手段？
    │         直接路径走不通时有什么替代方案？
    ↓
[3. 执行] — 按计划行动。不只是"查数据"，更是"做事"
    │         （调 API、跑脚本、写文件、组合多步操作）
    ↓
[4. 验证] — 问题真的解决了吗？（不是"我回答了"，是"事情做成了"）
    ├── 没解决 → 回到步骤 2，想别的办法
    └── 解决了 ↓
[5. 告知] — 简洁告诉用户结果
    ↓
输出
```

关键区别：
- "回答"模式：目标 = 输出一段话 → "现在几点？" → 编一个时间
- "解决"模式：目标 = 让用户知道真实时间 → 跑脚本获取 → 告诉用户结果

---

## 具体场景对比

### 场景 1："现在几点"

| 模式 | 行为 |
|------|------|
| 当前 | LLM 编一个时间（如"下午3点"），或说"我不知道" |
| 目标 | 理解：用户要知道真实时间 → 规划：我没有时钟工具，但可以跑脚本 → 执行：`call_workspace_api` 或 terminal 跑 `datetime.now()` → 验证：拿到了真实时间 → 告知用户 |

### 场景 2："我有几个待办"

| 模式 | 行为 |
|------|------|
| 当前 | 调 `call_workspace_api GET /tasks` → 返回全量 JSON → 数 count → 回答 |
| 目标 | 理解：用户可能想知道"还有多少没做" → 规划：查未完成的 → 执行 → 验证：数字对得上 → 告知："你有 22 个未完成，其中 7 个高优" |

### 场景 3："帮我把这个文件整理一下"

| 模式 | 行为 |
|------|------|
| 当前 | 给建议："你可以按照 XX 方式整理" 或者 尝试 read_file → 路径错 → 编结果 |
| 目标 | 理解：哪个文件？整理成什么样？→ 追问确认 → 规划：读文件→分析结构→重组→写回 → 执行（真的动手改）→ 验证：文件确实改了 → 告知结果 |

### 场景 4："这个接口为什么报错"

| 模式 | 行为 |
|------|------|
| 当前 | 给一段通用建议文字（"可能是参数错误，建议检查 XX"） |
| 目标 | 理解：哪个接口？什么错误？→ 规划：读代码→找报错位置→分析原因 → 执行：真的读文件定位问题 → 验证：找到根因 → 告知：具体原因 + 修复建议（甚至直接修）|

### 场景 5："项目进展怎么样"

| 模式 | 行为 |
|------|------|
| 当前 | 不知道调什么工具 → 可能编造 / 可能说"我不知道" |
| 目标 | 理解：用户是 PM，管多个项目 → 规划：查待办状态→按项目分组→统计完成率 → 执行 → 验证：数据完整 → 告知：按项目的表格视图 |

---

## 技术设计方向

### 不再是"一个 while 循环调 LLM 等它回复"

当前代码的核心问题：

```python
while iteration < MAX:
    response = call_llm(messages)  # LLM 自己决定做什么
    if has_tool_calls:
        execute_tools()
    else:
        output_response()  # ← 目标是"输出文字"
```

这个结构有两个致命缺陷：
1. LLM **同时承担理解、规划、执行、验证的全部职责**。一个角色切换太频繁的 LLM 会混乱
2. **目标函数是"生成文字回复"**，不是"解决问题"。一旦 LLM 觉得"我可以回答了"就停下来，不管问题有没有真正解决

### 应该是：目标驱动的多阶段执行

```python
# 阶段 1：理解（定义"解决"意味着什么）
intent = understand(user_message, user_profile)
# intent.goal = "用户想知道真实时间"
# intent.solved_when = "获取到当前真实时间并告知用户"
if intent.needs_clarification:
    return ask_clarification(intent.questions)

# 阶段 2：规划（想办法，包括替代方案）
plan = make_plan(intent, available_tools)
# plan.steps = [
#   "没有时钟工具 → 用 terminal 跑 python 脚本获取时间",
#   "或者 → 调 workspace API 中如果有时间相关端点"
# ]
# plan.fallback = "如果都不行 → 诚实告诉用户我无法获取"

# 阶段 3：执行（真的去做，不只是"查"）
results = execute_plan(plan, guardrails)

# 阶段 4：验证（问题解决了吗？不是"我回复了吗"）
validation = verify_solved(results, intent)
# 判断标准：intent.solved_when 是否满足
if not validation.solved:
    plan = revise_plan(plan, validation.gaps)
    results = execute_plan(plan)  # 换个方案再试

# 阶段 5：告知（简洁告诉结果）
response = inform_user(results, intent)
```

### 核心转变：从"怎么回复"到"怎么解决"

| 环节 | 回答模式（当前） | 解决模式（目标） |
|------|------|------|
| 理解 | "用户问了什么" | "用户要解决什么问题" |
| 规划 | "用哪个工具能回答" | "怎样才算解决了？有几条路径？" |
| 执行 | 调一次工具拿数据 | 真正动手做（可能多步、可能写脚本） |
| 验证 | "我的回复有没有幻觉" | "问题真的解决了吗" |
| 输出 | 一段描述性文字 | 简洁的结果确认（重点是结果不是过程） |

### 每个阶段可以是不同的 prompt / 不同的 LLM call

- 理解阶段：用轻量 prompt（"分析用户意图，定义'解决'的标准"）
- 规划阶段：用规划 prompt（"基于目标和可用工具，输出解决路径，包括替代方案"）
- 执行阶段：传统 tool_call 循环（但执行目标从"拿数据"变成"做事"）
- 验证阶段：代码级检查 + "solved_when 条件是否满足"
- 告知阶段：简洁总结结果（不是描述过程）

### "创造力"在规划阶段

当前 agent 没有创造力的原因是它只看到"工具列表"，不会组合。规划阶段要教 agent：
- 没有直接工具？→ 想想能不能用现有工具的组合间接解决
- terminal 是万能后备 — 几乎任何事都可以通过跑脚本完成
- 一条路走不通？→ 规划中要有 fallback 路径
- 实在解决不了 → 诚实告知（但这是最后手段，不是第一反应）

---

## 验收标准（Phase 1 范围）

| # | AC |
|---|-----|
| 1 | 用户发消息后，agent 先做一次意图分析（不直接调工具），日志可见分析结果 |
| 2 | 意图分为 3 类：`simple_chat`（纯对话）/ `needs_action`（需要工具）/ `ambiguous`（需追问） |
| 3 | `simple_chat` 不给 LLM 工具 schema → 不会出现乱调工具的情况 |
| 4 | `ambiguous` 时 agent 追问 1 次确认意图，而不是猜测后直接行动 |
| 5 | `needs_action` 时生成结构化计划（goal + steps + fallback），注入到执行上下文中 |
| 6 | 计划中包含 fallback 路径——"如果 X 不行就试 Y" |
| 7 | 简单对话（"你好"、"谢谢"）延迟 < 当前（不能因为加了意图分析就变慢） |
| 8 | 意图分析 + 规划总耗费 < 200 tokens（轻量，不拖慢整体响应） |

---

## 与 079 的关系

079 做了：
- ✅ responder（呈现层）
- ✅ verifier（验证层，代码级比对）
- ✅ guardrails（执行保护）
- ✅ 文件分离（模块化）

080 Phase 1 新增：
- ❌→✅ 意图识别（Intent 分类器）
- ❌→✅ 规划层（结构化执行计划 + fallback）
- ❌→✅ 快速路径（simple_chat 跳过工具）

留给 081 Phase 2：
- ❌ 执行目标转变（从"拿数据回答"变成"做事解决问题"）
- ❌ 验证→补充执行的循环（判断"问题解决了"不是"回复没幻觉"）
- ❌ 创造力（工具组合 + 间接路径 + terminal 后备）

---

## 技术设计（Phase 1 精简版）

### 改动点：agent.py 的 while 循环前加两步

```python
# === NEW: Phase 1 — 意图识别 ===
intent = await classify_intent(user_message)
# intent = { type: "simple_chat"|"needs_action"|"ambiguous",
#             goal: "...", solved_when: "..." }

if intent["type"] == "ambiguous":
    yield "追问消息"
    return

if intent["type"] == "simple_chat":
    # 不给工具，纯对话
    yield from stream_response(messages, tools=None)
    return

# === NEW: Phase 1 — 规划 ===
plan = await make_plan(intent, available_tools)
# plan = { goal: "...", steps: [...], fallback: "..." }
# 注入到 system message 中，引导执行阶段

# === EXISTING: 执行循环（不改动，但执行时 LLM 能看到 plan）===
while iteration < MAX:
    ...
```

### 新增文件

| 文件 | 职责 | 大小 |
|------|------|------|
| `agent_intent.py` | Intent 分类器（一次 LLM call） | ~80 行 |
| `agent_planner.py` | 计划生成器（一次 LLM call） | ~100 行 |

### Intent 分类器设计

```python
INTENT_PROMPT = """分析用户消息，输出 JSON：
{
  "type": "simple_chat" | "needs_action" | "ambiguous",
  "goal": "用户想要达成什么（一句话）",
  "solved_when": "怎样才算解决了（一句话）",
  "clarification": "如果 ambiguous，要追问什么（可选）"
}

规则：
- 纯聊天/闲聊/感谢/打招呼 → simple_chat
- 需要查数据/做操作/调工具 → needs_action
- 说了要做什么但缺关键信息 → ambiguous
"""
```

### 计划生成器设计

```python
PLAN_PROMPT = """基于用户意图和可用工具，输出执行计划 JSON：
{
  "goal": "...",
  "steps": ["步骤1", "步骤2"],
  "fallback": "如果主路径失败的替代方案",
  "tools_needed": ["tool_name_1", "tool_name_2"]
}

可用工具：{tool_names}
用户意图：{intent.goal}
解决标准：{intent.solved_when}
"""
```

---

## 风险（Phase 1）

1. **增加 1-2 次 LLM 调用的延迟** — 用轻量 prompt + 限制 max_tokens=150 缓解
2. **分类器误判** — simple_chat 误判为 needs_action 无害（多给了工具而已）；needs_action 误判为 simple_chat 有害（该调工具没调）→ 倾向于让 needs_action 成为默认
3. **规划生成不稳定** — 用 JSON mode + 简单 schema 约束

---

## 参考来源

| 来源 | 学什么 |
|------|--------|
| Kiro Spec-Driven | 先理解后执行，意图结构化 |
| Codex Task-Oriented | 执行后验证，不通过不算完 → 081 |
| Claude Code 5-Step | PLAN→REVIEW→EXECUTE→VERIFY→COMMIT |
| Hermes-Agent | terminal 是万能后备、工具组合 → 081 |
| 岛主思想基石 | 用户是谁→想干什么→怎么帮他 |

---

## 一句话总结

> **在 agent 动手之前加一道"想"——分析意图、制定计划、区分快慢路径。**
