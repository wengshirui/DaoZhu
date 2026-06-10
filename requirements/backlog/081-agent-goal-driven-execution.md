# 081 — Agent 思维重塑 Phase 2：目标驱动执行

> 状态: 📋 待开发（依赖 #080 完成）
> 优先级: P0
> T-shirt Size: L
> 录入日期: 2026-06-10
> 前置: #080（意图识别 + 规划）

---

## 范围

080 让 agent 会"想"了（意图 + 计划），081 让 agent 会"做"——
按计划执行、验证问题是否真的解决了、没解决就换方案重试。

---

## 问题陈述（080 解决后剩余的）

080 之后 agent 有了意图和计划，但执行阶段还是老循环：
1. LLM 拿着 plan 去调工具，但**不检查计划是否完成**
2. 工具失败后**不会自动切换到 fallback 路径**
3. 验证标准还是"回复没幻觉"（079 的 verifier），不是"问题解决了"
4. agent 缺乏创造力——没有直接工具时不会想到间接路径（脚本/组合）

---

## 目标

执行阶段从"调工具等回复"变成"按计划做事、验证目标、失败重试"。

```
plan（来自 080）
    ↓
[执行] — 按 plan.steps 逐步执行
    ↓
[验证] — plan.solved_when 满足了吗？
    ├── 没满足 + 还有 fallback → 切换方案重试
    ├── 没满足 + 无方案 → 诚实告知用户
    └── 满足了 → 告知结果
```

---

## 验收标准

| # | AC |
|---|-----|
| 1 | 执行完后自动检查 `intent.solved_when` 是否满足，不满足时触发补充执行 |
| 2 | 主路径失败时自动切换到 plan.fallback，最多重试 2 次 |
| 3 | 没有直接工具时，agent 能想到替代方案（用 terminal 跑脚本、组合多个工具） |
| 4 | "帮我整理文件"时真的动手改文件，不是给建议 |
| 5 | 验证标准从"回复没幻觉"升级为"问题解决了" |
| 6 | 全流程日志：plan → execution → verification → retry/complete |
| 7 | 删除/修改类操作保留确认机制（不因为"积极行动"而跳过安全检查） |

---

## 技术方向

### 执行循环改造

```python
# 080 产出的 plan
plan = { goal, steps, fallback, solved_when }

# 执行
for attempt in range(MAX_ATTEMPTS):  # 最多 2 次
    results = await execute_with_tools(plan.steps, messages, tools)
    
    # 验证：问题解决了吗
    solved = await verify_solved(results, plan.solved_when)
    if solved:
        yield inform_user(results)
        return
    
    # 没解决：有 fallback 吗？
    if plan.fallback and attempt == 0:
        plan = revise_plan(plan, results.gaps)
        continue
    else:
        yield honest_failure(results)
        return
```

### verify_solved 升级

079 的 verifier 只检查"数字对不对、是否声称成功但工具失败"。
081 升级为判断 `solved_when`：

```python
async def verify_solved(results, solved_when: str) -> bool:
    # 层 1：代码级（工具全失败 → 肯定没解决）
    if all_tools_failed(results):
        return False
    # 层 2：轻量 LLM 判断
    prompt = f"执行结果：{results.summary}\n解决标准：{solved_when}\n问题解决了吗？(yes/no)"
    answer = await call_llm_simple(prompt, max_tokens=10)
    return "yes" in answer.lower()
```

### 创造力注入

在规划阶段（080）注入的 plan prompt 中强调：
- "如果没有直接工具，考虑用 terminal 跑脚本"
- "如果单个工具不够，考虑组合多个工具"

在执行阶段：当 plan.steps 中有"跑脚本"类步骤时，
自动构造 `call_workspace_api` 或 terminal 调用。

---

## 依赖

- #080 的 Intent + Plan 数据结构
- 079 的 verifier（升级但不重写）
- 079 的 guardrails（继续保护）

---

## 风险

1. **补充执行增加延迟** — 最多重试 1 次，总执行不超过 2 轮
2. **verify_solved 用 LLM 判断可能不准** — 先用代码级判断兜底
3. **过度行动** — 所有修改操作保留 permission gate
4. **成本增加** — 增加 1-2 次 LLM call，单次对话总计不超过 8 次 API 调用
