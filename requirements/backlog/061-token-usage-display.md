# 061 — 对话 Token 消耗 + 速度显示

> 状态: 🆕 待开发
> 优先级: P1
> T-shirt Size: S
> 录入日期: 2026-06-02

---

## 问题陈述

用户与岛管理员对话时，不知道每轮对话花了多少 token、花了多少钱、AI 回复速度如何。
缺少消耗感知会导致：
- 不知道长对话是否在"烧钱"
- 无法判断模型响应是否正常（卡了还是在想）
- 无法对比不同 provider 的性价比

## 用户故事

**As a** 岛主用户
**I want** 每轮对话结束后看到 token 消耗数和回复速度
**So that** 我能感知 AI 使用成本，判断响应是否正常

## 范围

### In Scope

- 后端：从 LLM API 响应的 `usage` 字段提取 token 数据
- 后端：通过 SSE 推送 token 统计到前端
- 前端：每轮 AI 回复下方显示统计信息（小字灰色）
- 显示内容：输入 token / 输出 token / 缓存命中 / 速度（token/s）/ 估算费用

### Out of Scope

- 累计统计面板（后续做）
- 费率配置界面（初期硬编码 DeepSeek 费率）
- 多模型费率对比

## 验收标准

1. **AC1**: 每轮 AI 回复下方显示 "⚡ 输入 XX / 输出 XX token · 缓存命中 XX · XX tok/s · ≈¥0.XX"
2. **AC2**: 输出速度实时可感知 — 从第一个 chunk 到最后一个 chunk 的时间计算 token/s
3. **AC3**: 缓存命中数 > 0 时显示（验证 #058 前缀优化生效），为 0 时不显示该项
4. **AC4**: 费用按 DeepSeek 当前费率估算（输入 ¥1/百万, 缓存 ¥0.1/百万, 输出 ¥2/百万）
5. **AC5**: 统计信息不干扰正常对话阅读（字号小、颜色淡、位置在气泡下方）

## 业务价值

- 用户获得成本透明感（建立信任）
- 验证 #058 缓存优化是否真正生效（缓存命中数可见）
- 帮助用户选择合适的使用方式（长对话 vs 短对话）

## T-Shirt Size

**S** — 后端从 API 响应提取 usage + 计时，前端渲染一行统计文字。
无 schema 变更，无新依赖。

## 技术提示

DeepSeek API 响应的 usage 字段：
```json
{
  "usage": {
    "prompt_tokens": 1234,
    "completion_tokens": 56,
    "prompt_cache_hit_tokens": 1000,
    "total_tokens": 1290
  }
}
```

速度计算：
```javascript
const startTime = Date.now();  // 收到第一个 chunk 时
const endTime = Date.now();    // 收到 done 时
const tokensPerSec = completionTokens / ((endTime - startTime) / 1000);
```
