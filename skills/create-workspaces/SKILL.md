# Create Workspaces Skill

> 岛主平台核心技能：为用户建造新工作区。

---

## 适用场景

- 用户说"帮我建一个 XXX 工作区"
- 用户需要某类应用（待办、记账、笔记、看板等）
- 用户想把某个开源项目变成本地工作区

---

## 工作流程（6 步）

### 1. 理解需求

提取：核心功能、关键实体、核心操作、UI 形态。

### 2. 搜索开源项目

- GitHub 英文关键词搜索，按 star 排序（≥ 50）
- 不限技术栈，任何语言都可参考其逻辑和数据模型
- 向用户展示 2-3 个候选项目，确认方案后再动手

### 3. 深入研究（不可跳过！）

> ⚠️ 桌面宠物教训：只看 README 就动手 → 参数错误 → 反复返工。

**必须做：**
- 克隆/下载项目，能跑就先跑起来看效果
- 阅读核心源码：数据格式、渲染逻辑、API 响应结构
- 提取可直接复用的代码（常量、CSS、数据结构）

**禁止：**
- ❌ 只看 README 就觉得"理解了"
- ❌ 凭记忆填参数（如尺寸、帧数、字段名）
- ❌ 用不同方案重写已有的成熟实现
- ❌ 发明开源项目没有的功能

### 4. 设计与实现

- 用岛主技术栈重写（FastAPI + SQLite + 纯 HTML/JS）
- 直接复用开源项目的常量/CSS/数据格式，不要"参考后自己写类似的"
- 遵循 `AGENTS.md` 的文件规模约束和编码规范
- 参考已有工作区（如 `workspaces/desktop-pet/`）的目录结构

### 5. 创建文件

必须产出：

```
workspaces/{id}/
├── app.py              # FastAPI 入口（≤ 100 行）
├── db.py               # 数据库连接（≤ 20 行）
├── schema.sql          # 表设计
├── routes/             # 按领域拆分
├── frontend/           # index.html + css/ + js/
├── workspace.json      # 元信息
└── README.md + AGENTS.md
```

AGENTS.md 必须包含：复用了哪个开源项目、关键参数、参考文件路径。

### 6. 测试验证

```bash
cd workspaces/{id}
../../.venv/Scripts/python.exe -m uvicorn app:app --port {port}
# 验证：API CRUD + 前端渲染 + 平台集成
```

---

## 踩坑记录

### 开源复用（核心教训）

| 错误做法 | 正确做法 |
|----------|----------|
| 只看 README 就动手 | 读源码，提取常量/CSS |
| "参考思路自己写" | 直接复用代码，参数对齐 |
| 发明数据源没有的功能 | 只做数据源支持的功能 |
| 前端反复调不对 | 停下来去看开源项目怎么做 |

### 技术踩坑

| 坑 | 解决 |
|----|------|
| 轻挂载时 lifespan 不执行 | app 创建时直接调 init_db() |
| 前端 API 路径轻挂载后 404 | 用动态 `API_BASE`（基于 pathname） |
| workspace.json 中文乱码 | 始终 `encoding="utf-8"` |
| SQLite 外键约束报错 | 缓存表不加外键 |

### 前端 API_BASE 兼容方案

```javascript
const API_BASE = (() => {
  const path = window.location.pathname;
  const base = path.endsWith('/') ? path : path + '/';
  return base + 'api/';
})();
```

### mode 选择

```
需要平台配置？ → lightweight
表 ≤ 3 且无额外依赖？ → lightweight
否则 → standard
```
