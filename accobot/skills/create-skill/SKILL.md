---
name: create-skill
description: 创建新 Skill 的标准流程和格式规范。当用户要求保存操作流程为 Skill 时使用。
version: 1.0.0
category: meta
tags: [skill, 创建, 模板, 规范]
---

# 创建新 Skill

## 概述

当用户修正了你的操作步骤、教你一个新流程、或明确说"保存为 Skill"时，使用此流程创建一个新的 Skill。Skill 是可复用的操作流程知识，下次遇到类似任务时自动加载执行。

## 何时使用

- 用户说"把这个流程保存下来"、"记住这个操作"、"保存为 Skill"
- 用户修正了你的操作步骤后，你主动提议保存
- 用户描述了一个重复性操作流程（如"每月报税流程"、"开票步骤"）
- 用户分享了某个外部系统的操作方法

## 创建步骤

### 1. 确定 Skill 名称

- 使用中文，简洁明了
- 格式：`{系统/场景}-{操作}`
- 示例：`广东电子税务局-增值税申报`、`招商银行-下载回单`、`餐饮业-月末结账`

### 2. 编写 SKILL.md 内容

必须包含 YAML frontmatter + Markdown 正文：

```markdown
---
name: skill名称
description: 一句话描述（不超过80字）
version: 1.0.0
category: 分类（tax/journal/reconciliation/browser/general）
tags: [标签1, 标签2]
requires_tools: [需要的工具名]
---

# 标题

## 前置条件
- 列出执行此流程前需要满足的条件

## 操作步骤
1. 第一步
2. 第二步
3. ...

## 注意事项
- 容易出错的地方
- 特殊情况处理
```

### 3. 调用 skill_manage 创建

```
skill_manage(
    action="create",
    name="skill名称",
    content="完整的 SKILL.md 内容（含 frontmatter）",
    category="分类名"  // 可选
)
```

### 4. 确认创建成功

告诉用户 Skill 已保存，下次遇到类似任务会自动使用。

## 格式规范

| 字段 | 要求 |
|------|------|
| name | 必填，≤64 字符 |
| description | 必填，≤80 字符，一句话说明用途 |
| version | 建议填 1.0.0 |
| category | 建议填（tax/journal/reconciliation/browser/general） |
| tags | 建议填 2-5 个标签 |
| requires_tools | 如果依赖特定工具（如 browser），列出来 |
| 正文 | 必须有内容，建议包含"前置条件"+"操作步骤"+"注意事项" |

## 分类参考

| category | 适用场景 |
|----------|---------|
| tax | 报税、税务局操作、税额计算流程 |
| journal | 做账、分录模板、结转流程 |
| reconciliation | 对账、银行流水处理 |
| browser | 需要 Playwright 操作外部网站的流程 |
| report | 报表生成、数据导出 |
| general | 通用流程、公司内部规则 |

## 常见错误

1. **description 太长** — 超过 80 字符会被拒绝，用一句话概括
2. **忘记 frontmatter** — 必须以 `---` 开头，否则无法被索引
3. **name 和文件夹名不一致** — name 字段值就是文件夹名，保持一致
4. **内容太空泛** — Skill 要具体到可执行，不是泛泛的知识介绍

## 示例

用户说："帮我记住，招行网银下载回单要先点'回单管理'再选日期范围"

你应该创建：

```
skill_manage(
    action="create",
    name="招商银行-下载回单",
    content="---\nname: 招商银行-下载回单\ndescription: 在招商银行企业网银下载电子回单的操作流程\nversion: 1.0.0\ncategory: browser\ntags: [招行, 回单, 网银]\nrequires_tools: [mcp_playwright_browser_navigate, mcp_playwright_browser_click]\n---\n\n# 招商银行 — 下载电子回单\n\n## 前置条件\n- 用户已登录招商银行企业网银\n- Playwright 浏览器已连接\n\n## 操作步骤\n1. 点击左侧菜单「回单管理」\n2. 选择日期范围\n3. 点击「查询」\n4. 勾选需要的回单\n5. 点击「下载」\n\n## 注意事项\n- 一次最多下载 50 张\n- PDF 格式，下载后自动保存到账套文件夹"
)
```
