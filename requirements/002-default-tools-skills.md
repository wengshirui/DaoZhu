# REQ-002: 平台默认工具与技能

> Intake ID: 2025-05-25-default-tools-skills

---

## 原始需求（Verbatim）

提供默认工具 playwright，默认 skill create-skill、create-workspaces（后续自定义）。

---

## 提取意图

平台需要预装一组开箱即用的工具（MCP）和技能（Skill），让管家具备基础能力：
- **工具层**：playwright（浏览器自动化）
- **技能层**：create-skill（创建新技能）、create-workspaces（创建新工作区）、frontend-design（前端 UI 设计）

---

## 开放问题

| # | 模块 | 问题 | AI 猜测 | 答案 |
|---|------|------|---------|------|
| 1 | 用户与现状 | 用户目前如何让管家获得新能力？没有默认技能时管家能做什么？ | 目前管家无任何能力，用户无法使用 AI 建造功能 | |
| 2 | 范围与影响 | playwright 工具的使用场景是什么？管家用它来做什么具体操作？ | 用于搜索 GitHub/Gitee 开源项目、抓取页面信息、验证工作区前端 | |
| 3 | 范围与影响 | create-skill 技能需要支持哪些类型的技能创建？技能的格式规范是什么？ | 参考 Hermes 的 SKILL.md 格式，包含 frontmatter + 指令正文 | |
| 4 | 业务规则 | 默认工具/技能是否允许用户禁用或卸载？还是强制内置？ | 默认内置但允许禁用，不允许删除 | |
| 5 | 业务规则 | 后续"自定义"技能的发布流程是怎样的？用户创建后如何生效？ | 保存到 skills/ 目录后立即可用，无需重启 | |

---

## 默认技能清单

| 技能 | 来源 | 用途 |
|------|------|------|
| `create-skill` | 自研 | 创建新技能（SKILL.md 格式） |
| `create-workspaces` | 自研 | 创建新工作区（搜索开源 + 自主建造） |
| `frontend-design` | [anthropics/skills](https://github.com/anthropics/skills) (16.6k forks) | 前端 UI 设计，生成高质量界面代码 |

### frontend-design 技能说明

来源于 Anthropic 官方 skills 仓库，已适配岛主平台：
- 原版支持 React/Vue 等框架
- 岛主版限定为纯 HTML/CSS/JS
- 增加中文排版适配、文件 ≤500 行约束、主题兼容要求
- 文件位置：`skills/frontend-design/SKILL.md`

---

## 状态

- [x] 需求录入
- [ ] 开放问题确认
- [ ] 需求提炼
- [ ] 移交开发
