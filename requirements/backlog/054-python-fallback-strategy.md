# 054 — Agent Python 兜底策略

> 状态: 🆕 待开发
> 优先级: P2
> T-shirt Size: S — 配置规则 + 已有 terminal 工具复用 + 安全边界控制；风险低
> 录入日期: 2026-05-29

---

## 问题陈述

Agent 在回答不了用户问题、联网也找不到好方案时，应该想到"用 Python 写个脚本来解决"。Python 几乎能解决所有计算、数据处理、自动化问题，这应该成为 Agent 的标准思维模式。

## 范围

**In Scope:**
- Agent 系统提示/技能中增加 Python 兜底规则
- Agent 可自动编写 Python 脚本并在本地执行
- 安全边界：不操作 DaoZhu 文件夹以外的文件（除非用户确认）
- 脚本执行结果反馈给用户

**Out of Scope:**
- 安装第三方 Python 包（初期仅用标准库 + 已安装依赖）
- 长时间运行的脚本（超过 30s 自动终止）

---

## User Story

> As a 岛主用户，I want Agent 在常规方式解决不了问题时，能自动想到写 Python 脚本来解决，so that 我能享受到 Python 的万能解决能力，而不需要自己写代码。

---

## 验收标准

1. Agent 系统提示中包含规则："当简单回答和联网都无法解决时，考虑用 Python 脚本解决"
2. Agent 生成的 Python 脚本默认在 DaoZhu 项目目录内执行
3. 脚本涉及 DaoZhu 文件夹以外的文件操作时，必须先征求用户确认
4. 脚本执行超过 30s 自动终止，提示用户
5. 执行结果（stdout/stderr）完整反馈给用户
6. 脚本文件保存到 `~/.daozhu/scripts/` 供后续复用
7. Agent 能根据执行结果判断是否成功，失败时自动修正重试（最多 2 次）

---

## 技术方案

### 实现方式

1. **技能文件**：新增 `skills/python-solver.md`，描述 Python 兜底策略和安全规则
2. **工具复用**：使用现有 `write_file` + `terminal`（或新增 `run_python` 工具）
3. **安全检查**：在执行前扫描脚本中的文件路径，超出 DaoZhu 目录的操作标记为需确认

### 安全规则

```
允许：
- 读写 DaoZhu/ 目录下的文件
- 网络请求（requests/urllib）
- 数据计算、文本处理
- 生成图表/报告

需确认：
- 操作 DaoZhu/ 以外的文件
- 安装新包（pip install）
- 系统级操作（注册表、服务等）

禁止：
- 删除系统文件
- 修改系统配置
- 执行未知来源的代码
```

---

## 依赖

- 现有 terminal 工具
- 现有 write_file 工具
- Agent 分层策略（053）— Python 兜底作为 Level 1.5 或 Level 2 的补充
