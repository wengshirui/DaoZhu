# DeepSeek-Reasonix 学习参考

> 来源: https://github.com/esengine/DeepSeek-Reasonix
> 研究日期: 2026-06-02
> 仓库位置: D:\python\DeepSeek-Reasonix

---

## 项目定位

面向终端的 DeepSeek 原生 AI coding agent。Go 编写，单二进制分发。
核心卖点：配置驱动（零硬编码模型）+ DeepSeek 前缀缓存优化（长会话省钱）。

---

## 架构概览

```
reasonix.toml (唯一配置入口)
    ↓
config.Load() → Provider Registry + Tool Registry + Permission Rules
    ↓
control.Controller (前端无关的核心)
    ↓
agent.Agent.Run() — 对话循环
    ├── provider.Stream() — 流式 LLM
    ├── tool.Execute() — 工具执行
    ├── permission.Gate — 三级权限
    ├── maybeCompact() — 自动压缩
    └── evidence.Collect() — 执行证据
    ↓
三前端共享 Controller:
    - cli (终端 TUI)
    - serve (HTTP/SSE)
    - desktop (Wails GUI)
```

---

## 核心设计思想

### 1. 前缀缓存是第一公民

> "the system-prompt prefix must stay byte-stable across turns so DeepSeek's
> automatic prefix cache stays warm. Never mutate it mid-session."

- System prompt = 稳定前缀（tools schema + 记忆 + 项目描述）
- 动态内容（当前对话）只在尾部追加
- 工具 schema 也是前缀的一部分，不能中途改变
- 结果：DeepSeek 命中缓存后输入费用降 90%

### 2. 会话压缩（Compaction）

**触发**：prompt_tokens > context_window × 0.8

**机制**：
1. 取出旧消息（system 和最近 N 条之间的部分）
2. 用 LLM 压缩为结构化摘要（Goal/Decisions/Files/Errors/Next）
3. 替换原始消息：`[system] + [summary] + [recent_tail]`
4. 归档被删除的原始消息

**防死循环**：如果连续 2 次触发压缩，说明 system prompt 本身太大，暂停自动压缩并警告。

**关键参数**：
```go
defaultCompactRatio  = 0.8    // 触发阈值
defaultTailTokens    = 16384  // 保留尾部 token 数
minRecentKeep        = 2      // 最少保留消息数
```

### 3. 配置驱动（零硬编码）

- Provider = 接口 + 工厂注册（`kind = "openai"` 覆盖所有兼容端点）
- Tool = 接口 + Registry（compile-time builtin + runtime plugin）
- 添加新模型 = 添加配置，不改代码
- 添加新工具 = 实现接口 + `init()` 注册

### 4. Permission Gate

```toml
[permissions]
mode  = "ask"                                # 默认：询问
deny  = ["bash(rm -rf*)", "bash(git push*)"] # 永远拒绝
allow = ["bash(go test*)"]                   # 永远放行
```

- 每次工具调用前经过 Gate
- 支持 glob 模式匹配命令参数
- 三级：allow / ask / deny

### 5. Skills = Markdown 剧本

- 存放在 `.reasonix/skills/<name>/SKILL.md`
- 用 frontmatter 声明元数据（name, description, runAs）
- 两种执行模式：
  - `inline`: 内容折叠进当前 turn（快，共享上下文）
  - `subagent`: 独立子循环，只返回最终结果（隔离，安全）

### 6. 多模型协同

- executor（执行器）：处理具体操作，用便宜的 flash 模型
- planner（规划器）：做高层决策，用强力的 pro 模型
- 各自维护独立 session，缓存互不干扰

---

## 岛主已吸收 / 待吸收对照表

| Reasonix 特性 | 岛主现状 | 行动 |
|---|---|---|
| 前缀缓存优化 | ❌ 每轮重拼 system prompt | → #058 |
| 会话自动压缩 | ❌ 到上限就截断/报错 | → #059 |
| Permission Gate | 部分（仅删除确认） | → #060（整合 #054） |
| 配置驱动 provider | ✅ 已有（#045） | — |
| Skills 系统 | ✅ 已有 | 可学 subagent 模式（后续） |
| 多角色协同 | ✅ 已有（#051 质检） | 可学 planner 独立 session |
| 单二进制分发 | ✅ 已有（launcher.py + PyInstaller） | — |
| 工具 schema 注册 | ✅ 已有（tools/registry.py） | — |
| MCP 插件 | ❌ | 后续可做（优先级低） |
| AGENTS.md 项目记忆 | ✅ 已有（各工作区 AGENTS.md） | — |

---

## 关键代码位置

| 功能 | 文件 | 可复用度 |
|------|------|---------|
| 压缩算法 | `internal/agent/compact.go` | 高（逻辑可直译 Python） |
| 压缩 Prompt | `compact.go:summarySystemPrompt` | 直接复用 |
| 权限匹配 | `internal/permission/` | 高（glob 模式匹配） |
| Session 管理 | `internal/agent/session.go` | 参考设计 |
| 工具注册 | `internal/tool/` | 岛主已有类似 |
| Skill 加载 | `internal/skill/skill.go` | 参考 subagent 模式 |
| 配置解析 | `internal/config/` | TOML 方案，岛主用 JSON |

---

## 不适合岛主借鉴的

1. **Go 单二进制** — 岛主是 Python 生态，不需要追求零依赖
2. **compile-time 工具注册** — Go 的 `init()` 模式，Python 用 import-time 注册已经做了
3. **Wails 桌面** — 岛主用 PySide6，场景不同
4. **TOML 配置** — 岛主用 JSON + SQLite，已经够用
