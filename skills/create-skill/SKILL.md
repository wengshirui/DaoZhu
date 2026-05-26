# Create Skill 技能

> 元技能：创建和管理其他技能

---

## 描述

帮助用户创建新的技能文件（SKILL.md）。可以从网上搜索现有 skill 并安装，
也可以根据用户需求从零创建自定义 skill。

---

## 适用场景

- 用户说"帮我找一个 XXX 的 skill"
- 用户说"创建一个新技能"
- 用户说"安装 XXX skill"

---

## 工作流程

### 搜索并安装现有 Skill

1. 用户描述需要什么能力
2. 搜索 GitHub/网络上的 SKILL.md 文件或相关项目
3. 展示搜索结果让用户选择
4. 下载/改写为岛主格式的 SKILL.md
5. 保存到 `skills/{skill-name}/SKILL.md`

### 从零创建 Skill

1. 理解用户需要什么能力
2. 设计 skill 的指令内容
3. 生成 SKILL.md 文件
4. 保存到 `skills/{skill-name}/SKILL.md`

---

## SKILL.md 格式规范

```markdown
# {Skill 名称}

> 一句话描述

---

## 描述

详细说明这个 skill 做什么。

---

## 适用场景

- 场景 1
- 场景 2

---

## 工作流程

具体的执行步骤和指令。

---
```

---

## 使用工具

创建 skill 时使用 `write_file` 工具：
- 路径格式：`skills/{skill-id}/SKILL.md`
- 例如：`skills/weather/SKILL.md`

---

## 注意事项

- Skill ID 使用 kebab-case（如 `create-workspaces`）
- SKILL.md 必须是 UTF-8 编码
- 描述要简洁（≤ 60 字符）
- 创建后立即可用（skill_loader 自动发现）
