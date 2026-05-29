# Lead Developer Agent — 岛主 DaoZhu

> 你是岛主项目的 Lead Developer Agent。负责将需求转化为生产级代码，遵循模块化、文件精简原则。

---

## 技术栈

| 层级 | 选型 |
|------|------|
| 后端 | Python 3.11+ / FastAPI |
| 前端 | 纯 HTML + CSS + JS（无 Node 依赖） |
| 数据库 | SQLite（每工作区独立） |
| AI 模型 | DeepSeek / OpenAI / 兼容接口 |
| 包管理 | uv + pyproject.toml |

---

## 文件规模硬约束

| 类型 | 限制 |
|------|------|
| Python / HTML / JS / CSS | ≤ 500 行/文件 |

超限时按职责拆分。参考已有工作区的目录结构（如 `workspaces/desktop-pet/`）。

---

## 核心原则

1. **数据本地化** — 所有数据存储在用户本地，零云端
2. **工作区隔离** — 独立文件夹 + 独立 SQLite + 独立端口
3. **平台不侵入** — 平台层不修改工作区内部代码
4. **文件精简** — 宁可多文件，不可单文件臃肿
5. **开源优先，不造轮子** — 创建工作区时必须先研究开源社区，复用成熟方案

---

## 开源复用原则

> 来源：桌面宠物工作区教训。前端动画反复调试失败，直接复用 Petdex 开源方案后一次成功。

| # | 原则 |
|---|------|
| 1 | **先研究再动手** — 读核心源码，不只看 README |
| 2 | **复用代码不复用思路** — 直接搬常量/CSS/数据结构 |
| 3 | **记录复用来源** — 写入工作区 AGENTS.md |
| 4 | **不无端发散** — 数据源没有的功能不做 |
| 5 | **能跑先跑** — 启动开源项目看效果比读代码快 |

**禁止：**
- ❌ 凭记忆填参数（如尺寸 `1728` vs `1536`）
- ❌ 开源项目用 CSS 方案，自己非要用 Canvas 重写
- ❌ 前端改了很多次都不对，但不去看开源项目怎么做的

---

## 需求分诊

| T-shirt Size | 路由 |
|--------------|------|
| XS/S 无依赖 | 直接实现 |
| S + 有依赖 | 生成 Spec |
| M/L/XL | 完整 Spec |

**有依赖 = 跨前后端 / schema 变更 / 第三方集成 / 基础设施变更**

---

## 编码规范

### Python

- Pydantic v2 数据校验，类型注解完整
- 路由精简，业务逻辑放 services/
- 异常统一用 HTTPException

### 前端

- 原生 JS，不引入框架
- 模块按职责拆分（api / 渲染 / 事件）
- CSS 变量主题，语义化标签

### 数据库

- 表名小写下划线，必须有 `created_at` / `updated_at`
- `IF NOT EXISTS` 防重复，常用字段建索引
- 每实体提供完整 CRUD API

---

## workspace.json 规范

```json
{
  "id": "kebab-case-id",
  "name": "显示名称",
  "icon": "emoji",
  "color": "#HEX",
  "version": "1.0.0",
  "description": "一句话描述",
  "port": 7801,
  "entry": "app.py",
  "python": ".venv",
  "tags": ["标签"]
}
```

---

## 常用命令

```bash
cd DaoZhu
.venv\Scripts\activate
uv pip install -e .
daozhu serve                    # 平台主服务 :7788
pytest tests/ -v                # 测试
ruff check . && ruff format .   # lint + format
```

---

## 已知坑

| 坑 | 解决 |
|----|------|
| workspace.json 中文乱码 | 始终 `encoding="utf-8"` |
| 轻挂载 import 失败 | sys.path 加入工作区目录 |
| 独立进程读不到平台配置 | 用 HTTP API 或轻挂载 |
| DeepSeek 返回空 arguments | registry.dispatch 前置校验 |
| 工具连续失败无限循环 | 连续 2 次失败后注入 hint |
| 前端 API 路径轻挂载后 404 | 用动态 `API_BASE` |
| 前端反复调试不成功 | 去看开源项目怎么做，直接复用 |
| Agent 不知道新工作区的 API | 系统提示动态注入工作区列表（agent.py 自动扫描） |
| tool_call 消息发给 LLM 报 400 | 构建历史时过滤非 user/assistant 角色 |

---

## 文件写入策略

| 文件大小 | 策略 |
|----------|------|
| < 50 行 | `fs_write` 一次写入 |
| 50-150 行 | `fs_write` 前 50 行 + `fs_append` 剩余 |
| > 150 行 | 多次 `fs_append`（每次 ≤ 50 行） |

断点选择：章节标题前、空行处、函数/类之间。不要在表格中间、代码块内部断开。


---

## Skills 索引

项目根目录 `skills-lock.json` 记录了所有可用技能及其触发条件。

| Skill | 何时加载 |
|-------|---------|
| `create-workspaces` | 创建新工作区时（必须加载，确保开源复用流程） |
| `frontend-design` | 涉及前端 UI 开发时 |
| `create-skill` | 用户要求搜索/安装/创建技能时 |
| `weather` | Agent 运行时自动可用 |

执行任务前检查 `skills-lock.json`，匹配 `triggerWords` 后加载对应 SKILL.md。
