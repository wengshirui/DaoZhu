# 058 — DeepSeek 前缀缓存优化

> 来源: DeepSeek-Reasonix 项目 `internal/agent/compact.go` + `REASONIX.md`
> 状态: 🆕 待开发
> 优先级: P1
> T-shirt Size: S
> 录入日期: 2026-06-02

---

## 问题陈述

岛主每轮对话都重新拼接 system prompt（含动态工作区列表、统计数据、技能摘要），导致
DeepSeek 的自动前缀缓存无法命中。前缀缓存命中后只计尾部 token 费用（约省 90% 输入费用），
但要求每次请求的前 N 个 token 完全一致。

当前 `agent.py` 的 system prompt 构建顺序：
1. SYSTEM_PROMPT（固定）
2. skills_summary（较少变动）
3. 工作区列表（每次启动可能变）
4. stats_context（实时变动）
5. memory_context（每轮不同）

这导致即使连续对话，每轮的 system prompt 都有细微变化，缓存从不命中。

## 用户故事

**As a** 岛主用户
**I want** AI 对话的 token 成本更低
**So that** 长对话和频繁使用不会产生高额 API 费用

## 范围

### In Scope

- 将 system prompt 分为"稳定前缀"和"动态尾部"两段
- 稳定前缀：SYSTEM_PROMPT + 工具 schema（这两个在一轮对话内不变）
- 动态尾部：工作区列表 + skills + memory + stats（放到 user message 或尾部）
- 确保同一轮对话内，前缀部分字节级稳定

### Out of Scope

- 跨对话的缓存优化（DeepSeek 自动处理）
- 修改 DeepSeek API 调用方式（保持 OpenAI 兼容）

## 验收标准

1. **AC1**: 同一轮对话中连续的 LLM 调用，system prompt 的前 N 个字符完全相同
   （N = SYSTEM_PROMPT 长度），可通过日志验证
2. **AC2**: 动态内容（工作区列表、memory）移到 system prompt 尾部或独立的
   user message 中，不影响 AI 回复质量
3. **AC3**: 实现后的 AI 行为不退化 — Agent 仍能正确列出工作区、使用记忆
4. **AC4**: 在连续工具调用场景（如 3+ 轮工具调用），DeepSeek 返回的
   `usage.prompt_cache_hit_tokens` > 0（可从 API 响应中读取验证）

## 业务价值

- DeepSeek 前缀缓存命中后输入费用降 90%（0.27元/百万token → 0.027元）
- 对长对话（10+ 轮工具调用）影响显著：预估每次复杂任务省 ¥0.1-0.5
- 月度成本预估降低 30-50%

## T-Shirt Size

**S** — 仅重构 `agent.py` 中 system prompt 拼接顺序，不改 API 调用逻辑，不改数据库

## 技术提示（供开发参考）

参考 Reasonix 的做法：
- `REASONIX.md`: "the system-prompt prefix must stay byte-stable across turns"
- `control.Compose`: 分离稳定前缀 vs 动态 turn tail
- 关键思路：工具 schema 也是前缀的一部分（每次一样），所以不要在中间插入变化内容

实现方式：
```python
# 稳定前缀（字节级不变）
stable_prefix = SYSTEM_PROMPT  # 固定文本

# 动态注入改为放在消息列表里，而不是拼进 system prompt
dynamic_context_msg = {
    "role": "system",  # 或用 user 角色
    "content": f"[当前环境信息]\n{workspace_list}\n{skills_summary}\n{stats_context}"
}
# 放在 messages 列表中、system prompt 之后
```
