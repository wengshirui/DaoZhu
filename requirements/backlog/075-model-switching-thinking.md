# 075 — 模型切换 + 深度思考模式

> 状态: 🆕 待开发
> 优先级: P1
> T-shirt Size: S
> 录入日期: 2026-06-08

---

## 问题陈述

当前岛主用户只能切换 AI Provider（DeepSeek / 智谱 / Ollama / OpenAI），但无法切换同一 Provider 下的不同模型（如 DeepSeek Chat vs DeepSeek Reasoner），也无法控制是否启用"深度思考/推理"模式。

实际问题：
1. 用户想要 DeepSeek Reasoner（推理增强模型）做复杂任务，但没有切换入口
2. 用户想临时关闭/开启"思考模式"来控制 token 消耗和响应速度
3. 不同模型有不同的能力和价格，用户需要手动选择
4. 设置面板只有 Provider 下拉框，缺少模型选择和推理开关

## 用户故事

**As a** 岛主用户
**I want** 在设置中自由切换 AI 模型，并能开关深度思考模式
**So that** 简单对话用便宜模型省钱，复杂推理用强模型保证质量

## 范围

### In Scope

- 设置面板新增"模型选择"下拉框，根据选中的 Provider 动态加载可用模型列表
- 设置面板新增"深度思考/推理模式"开关（toggle）
- 配置持久化：`ai.model`（模型名）和 `ai.thinking`（布尔，是否启用推理）
- DeepSeek Provider 支持至少两个模型：`deepseek-chat`（普通）和 `deepseek-reasoner`（推理）
- 其他 Provider 的模型列表（OpenAI: gpt-4o / gpt-4o-mini；智谱: glm-4-plus / glm-4-flash）
- 前端发送消息时将 thinking 参数传给后端
- 后端在 LLM 调用时根据 thinking 模式调整请求参数（temperature、thinking 参数等）

### Out of Scope

- 自动模型推荐（属于 #063 智能路由）
- 模型性能评测/对比
- 自定义模型名称输入（保持下拉选择，降低复杂度）

## 验收标准

1. **AC1**: 设置面板在 Provider 下拉框下方显示"模型"下拉框，选项随 Provider 变化
2. **AC2**: 选择 DeepSeek 时，模型选项包含 `deepseek-chat` 和 `deepseek-reasoner`
3. **AC3**: 设置面板有"深度思考/推理模式"开关，默认关闭
4. **AC4**: 修改模型或思考开关后点击保存，配置持久化到 config.json
5. **AC5**: 发送消息时，后端使用选中的模型和思考模式调用 LLM
6. **AC6**: 刷新页面或重启应用后，模型选择和思考开关状态保持

## 技术要点

- `config.json` 新增字段：`ai.model`（已有，需扩展默认值）、`ai.thinking`（新增）
- `daozhu/config.py` 中 `PROVIDERS` 表新增 `models` 字段，每个 Provider 列出可用模型
- 前端 `app.js` 的 `_showSettings()` 新增模型下拉 + 思考开关 UI
- `agent.py` 在调用 LLM 时读取 `ai.thinking` 决定是否传 `reasoning_effort` 等参数

## 业务价值

- 用户可根据任务难度自由选择性价比最优的模型
- 深度思考模式显著提升复杂推理任务质量（代码生成、逻辑分析）
- 为后续 #063 智能路由提供模型池基础

## 依赖

- #045 多模型 Provider（已完成）
- config 系统（已有，需扩展字段）
