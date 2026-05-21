# REQ-016 Skill 系统（操作流程知识库）

**状态：** ✔️ Done  
**优先级：** P0（可扩展性基础 — 不同企业/地区的财务操作差异只能通过 Skill 解决）  
**T-Shirt Size：** L - 涉及文件系统、prompt 注入、Agent 工具、索引缓存；是 MCP 和自动化的前置依赖

---

## 问题陈述

不同企业使用不同的财务系统（金蝶/用友/浪潮）、不同地区的税务局操作流程不同、不同行业的分录模板不同。这些差异不可能全部内置到代码中。需要一个"操作流程知识库"机制，让用户（或 AI 自己）可以把成功的操作流程保存下来，下次遇到类似任务时自动加载执行。

## 用户故事

**As a** 代账会计  
**I want** 把"在广东省电子税务局申报增值税"的操作步骤保存为一个 Skill  
**So that** 下次报税时 AI 直接按这个流程操作，不用我每次重新教它

## 范围

### In Scope

**Skill 存储：**
- Skill 以 Markdown 文件存储在 `~/.accobot/skills/` 目录
- 每个 Skill 一个文件夹，包含 `SKILL.md`（主文件）+ 可选的 `references/`、`scripts/`、`templates/` 子目录
- SKILL.md 使用 YAML frontmatter 记录元数据（name、description、tags、category）

**Skill 索引（系统提示词注入）：**
- Agent 启动时扫描所有 Skill，构建索引（名称 + 一句话描述）
- 索引注入 system prompt，让 Agent 知道有哪些 Skill 可用
- 索引总 token 控制在 500 以内（只放名称和描述，不放全文）

**Skill 按需加载：**
- Agent 判断当前任务匹配某个 Skill 时，调用 `skill_view` 加载全文
- 加载的 Skill 内容作为 **user message** 注入（不是 system prompt），保护 prompt cache
- 加载后 Agent 按 Skill 中的步骤执行

**Skill 管理工具：**
- `skill_list` — 列出所有可用 Skill（名称 + 描述 + 分类）
- `skill_view` — 查看某个 Skill 的完整内容
- `skill_manage` — 创建/编辑/删除 Skill（Agent 可自主调用）

**Skill 自动创建：**
- 用户修正了 Agent 的操作流程后，Agent 主动提议"要不要保存为 Skill"
- 用户确认后，Agent 调用 `skill_manage(action="create")` 保存

**预置 Skill：**
- 项目内置几个通用财务 Skill（随代码分发，只读）
- 用户创建的 Skill 在 `~/.accobot/skills/`（可读写）

### Out of Scope

- Skill 市场/社区分享（后续迭代）
- Skill 版本管理（git 级别的 diff/merge）
- Skill 自动过期/归档（Hermes 的 curator 机制，暂不需要）

## SKILL.md 格式规范

```yaml
---
name: 广东电子税务局-增值税申报
description: 在广东省电子税务局网站完成小规模纳税人增值税申报的完整流程
version: 1.0.0
category: tax
tags: [增值税, 广东, 小规模, 电子税务局]
requires_tools: [browser_open, browser_click, browser_fill]
---

# 广东电子税务局 — 增值税申报

## 前置条件
- 用户已在浏览器中登录电子税务局
- 当期增值税已通过 `calculate_vat` 计算完成

## 操作步骤
1. 打开申报页面：我要办税 → 税费申报及缴纳 → 增值税申报
2. 填写销售额：从 AccoBot 计算结果中获取本期收入
3. 确认税额：系统自动计算，核对与 AccoBot 计算结果一致
4. 提交申报：点击"申报"按钮（需用户确认）

## 注意事项
- 季度收入 ≤ 30万免征增值税，申报时仍需填写但税额为0
- 提交前必须暂停让用户确认数据
```

## 验收标准

1. **AC-1：Skill 目录扫描** — Agent 启动时自动扫描 `~/.accobot/skills/` 目录，识别所有包含 `SKILL.md` 的子文件夹，构建索引
2. **AC-2：索引注入** — system prompt 中包含所有 Skill 的名称和描述列表，格式紧凑（每个 Skill 一行），总长度不超过 500 token
3. **AC-3：按需加载** — Agent 调用 `skill_view("广东电子税务局-增值税申报")` 后，该 Skill 的完整内容作为下一条 user message 注入对话
4. **AC-4：Skill 创建** — Agent 调用 `skill_manage(action="create", name="xxx", content="...")` 后，在 `~/.accobot/skills/xxx/SKILL.md` 创建文件，frontmatter 格式正确
5. **AC-5：Skill 编辑** — Agent 调用 `skill_manage(action="edit", name="xxx", content="...")` 后，更新已有 Skill 内容
6. **AC-6：Skill 删除** — Agent 调用 `skill_manage(action="delete", name="xxx")` 后，删除对应 Skill 文件夹
7. **AC-7：预置 Skill 只读** — 项目内置的 Skill（`accobot/skills/` 目录下）不可被 `skill_manage` 修改或删除
8. **AC-8：Skill 列表工具** — `skill_list()` 返回所有 Skill 的名称、描述、分类，支持按 category 筛选
9. **AC-9：frontmatter 校验** — 创建 Skill 时校验 frontmatter 必须包含 name 和 description，description 不超过 80 字符
10. **AC-10：主动提议保存** — 当用户修正了 Agent 的操作步骤（如"不对，应该先点XX再点YY"），Agent 在完成任务后主动问"要不要把这个流程保存为 Skill？"

## 文件结构

```
~/.accobot/skills/                          # 用户 Skill（可读写）
├── 广东电子税务局-增值税申报/
│   ├── SKILL.md
│   └── screenshots/                        # 参考截图（可选）
├── 招商银行-下载回单/
│   ├── SKILL.md
│   └── scripts/                            # 辅助脚本（可选）
├── 餐饮业-常见分录模板/
│   └── SKILL.md
└── 差旅费报销标准/
    └── SKILL.md

accobot/skills/                             # 内置 Skill（只读，随代码分发）
├── 通用分录模板/
│   └── SKILL.md
├── 期末结转流程/
│   └── SKILL.md
└── 银行对账流程/
    └── SKILL.md
```

## 依赖

- REQ-001（Agent 核心框架 — system prompt 注入点）
- REQ-011（浏览器自动化 — Skill 中引用的 browser 工具）
- REQ-012（记忆系统 — Skill 与记忆互补，记忆是隐式的，Skill 是显式的）

## 开放问题

| # | 问题 | 待定方案 |
|---|------|---------|
| 1 | Skill 内容过长怎么办？ | 建议限制 SKILL.md 不超过 3000 字符，超出部分放 references/ |
| 2 | 多个 Skill 匹配同一任务时如何选择？ | 建议 Agent 自行判断最匹配的，或列出让用户选 |
| 3 | Skill 中的操作步骤如何与 Playwright 联动？ | Skill 描述"做什么"，Agent 翻译为具体的 browser 工具调用 |
