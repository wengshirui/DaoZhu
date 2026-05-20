# REQ-001 Agent 核心框架

**状态：** ✔️ Done  
**优先级：** P0（基础设施）  
**T-Shirt Size：** L - 核心架构，所有功能依赖此模块；需要设计好扩展点

---

## 问题陈述

AccoBot 需要一个 AI Agent 核心引擎，能够理解用户的自然语言指令，调用对应的财务工具完成任务，并以对话形式返回结果。参考 Hermes Agent 的架构，但针对财务垂直领域做精简和优化。

## 用户故事

**As a** 任意用户（老板/会计/财务人员）  
**I want** 用自然语言描述我的财务需求  
**So that** AI 自动理解意图并调用正确的工具完成操作，无需我了解专业术语或操作步骤

## 范围

### In Scope

- 对话循环引擎（同步，支持流式输出）
- 工具注册/发现/调度机制
- 工具集（Toolset）分组管理
- 多模型支持（OpenAI 兼容接口，覆盖国产模型）
- 系统提示词管理（财务领域专用 system prompt）
- 消息历史管理
- 迭代预算控制（防止无限循环）
- 中断机制（用户可随时打断）
- 错误处理与重试

### Out of Scope

- 具体财务工具实现（REQ-002 ~ REQ-009）
- Web UI（REQ-010）
- 消息平台接入（REQ-013）

## 验收标准

1. **AC-1：对话基本流程** — 用户输入自然语言，Agent 能正确识别意图并调用对应工具，返回结构化结果
2. **AC-2：工具注册** — 新增一个工具只需创建 `tools/xxx.py` 文件并调用 `registry.register()`，无需修改其他文件
3. **AC-3：多模型切换** — 通过配置文件切换 LLM 提供商（OpenAI/DeepSeek/Qwen 等），无需改代码
4. **AC-4：流式输出** — Agent 回复支持逐 token 流式返回，CLI 和 WebSocket 均可消费
5. **AC-5：迭代控制** — 单次对话的工具调用次数不超过配置的 max_iterations，超出时优雅终止并告知用户
6. **AC-6：错误恢复** — 工具调用失败时，Agent 能向用户解释错误原因并建议替代方案，不会崩溃

## 依赖

- Python 3.11+
- openai SDK
- 配置系统（config.yaml + .env）

## 参考

- Hermes Agent: `run_agent.py`（AIAgent 类）
- Hermes Agent: `model_tools.py`（工具编排）
- Hermes Agent: `tools/registry.py`（注册中心）
- Hermes Agent: `toolsets.py`（工具集定义）
