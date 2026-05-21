# AccoBot 需求文档

本目录存放 AccoBot 项目的所有产品需求文档。

## 文档结构

| 文件 | 说明 |
|------|------|
| `REQ-001-agent-core.md` | Agent 核心框架需求 |
| `REQ-002-basic-config.md` | 基础配置（账套/科目/辅助核算） |
| `REQ-003-voucher.md` | 原始凭证管理 |
| `REQ-004-journal.md` | 做账（分录生成/审核/过账） |
| `REQ-005-reconciliation.md` | 对账 |
| `REQ-006-tax.md` | 报税 |
| `REQ-007-ledger.md` | 账簿查看 |
| `REQ-008-report.md` | 报表 |
| `REQ-009-analytics.md` | 数据分析 |
| `REQ-010-web-ui.md` | Web UI 交互 |
| `REQ-011-browser-automation.md` | 浏览器自动化（Playwright） |
| `REQ-012-memory-skills.md` | 记忆与技能系统 |
| `REQ-013-messaging.md` | 消息平台接入 |
| `REQ-014-learning.md` | 学习辅导功能 |
| `REQ-015-quality-check.md` | 质检与风控 |
| `REQ-016-skill-system.md` | Skill 系统（操作流程知识库） |
| `REQ-017-mcp-client.md` | MCP 客户端（外部工具连接器） |

## 需求状态

- 📝 Draft — 初稿
- 🔍 Review — 待确认
- ✅ Approved — 已确认
- 🚧 In Progress — 开发中
- ✔️ Done — 已完成
- 🔀 Merged — 已合并到其他需求

## 当前开发进度

| 需求 | 状态 | 说明 |
|------|------|------|
| REQ-001 Agent 核心框架 | ✔️ Done | 对话循环、工具注册/发现/调度、流式输出、多模型支持 |
| REQ-002 基础配置 | ✔️ Done | 数据库层✔️、Agent工具（科目/辅助核算/期间）✔️、Web API✔️、账套管理✔️、文件夹结构✔️、删除二次确认✔️ |
| REQ-003 原始凭证管理 | ✔️ Done | 凭证创建✔️、查询✔️、详情✔️、过账✔️、OCR识别✔️、附件管理✔️ |
| REQ-004 做账 | ✔️ Done | 智能分录生成✔️、借贷校验✔️、过账✔️、期末结转✔️、红冲✔️ |
| REQ-005 对账 | ✔️ Done | 银行流水导入✔️、自动匹配✔️、对账状态查看✔️ |
| REQ-006 报税 | ✔️ Done | 增值税计算✔️、附加税计算✔️、报税日历✔️ |
| REQ-007 账簿查看 | ✔️ Done | 余额查询✔️、明细账✔️、科目余额表✔️ |
| REQ-008 报表 | ✔️ Done | 利润表✔️、资产负债表✔️ |
| REQ-009 数据分析 | ✔️ Done | 费用结构分析✔️、收支对比✔️ |
| REQ-010 Web UI | ✔️ Done | 三栏布局✔️、对话✔️、设置引导✔️、账套管理✔️、待办提醒✔️、对话历史✔️、数据展示✔️、文件上传✔️、左右可折叠✔️ |
| REQ-011 浏览器自动化 | ✔️ Done | Playwright 工具✔️（open/snapshot/click/fill/screenshot/close），MCP 默认配置✔️，check_fn 门控，用户自行登录 |
| REQ-012 记忆与技能系统 | ✔️ Done | 记忆存取✔️（偏好/模式/规则）、遗忘✔️、知识点追踪✔️、学习进度✔️ |
| REQ-013 消息平台接入 | ✔️ Done | Gateway 框架✔️、MessageAdapter 接口✔️、企业微信/钉钉/飞书适配器骨架✔️、界面化配置✔️ |
| REQ-014 学习辅导 | 🔀 Merged | 合并到 REQ-012 实现（知识点记录✔️、掌握度追踪✔️、学习进度查看✔️） |
| REQ-015 质检与风控 | ✔️ Done | 凭证质检✔️（借贷平衡/大额现金/空摘要/科目余额方向异常） |
| REQ-016 Skill 系统 | ✔️ Done | Skill 存储✔️、目录扫描✔️、索引构建✔️、system prompt 注入✔️、skill_list/view/manage 工具✔️、预置 Skill✔️、只读保护✔️ |
| REQ-017 MCP 客户端 | ✔️ Done | 配置读取✔️、Stdio 连接✔️（持久化任务）、HTTP 连接✔️、工具发现注册✔️、工具调用✔️、超时控制✔️、重试✔️、环境变量插值✔️、优雅关闭✔️、Web UI 状态✔️、重连✔️ |

## 目标用户

所有类型的财务相关用户：
- 小微企业老板（不懂会计，AI 负责专业判断）
- 兼职/代账会计（效率优先，多账套管理）
- 企业内部财务人员（完整功能）

**核心理念：AI 负责专业性，用户只需表达意图。**
