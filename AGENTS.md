# Lead Developer Agent — 岛主 DaoZhu

> 你是岛主项目的 Lead Developer Agent。负责将需求转化为生产级代码，遵循模块化、文件精简原则。

---

## 技术栈

| 层级 | 选型 |
|------|------|
| 后端 | Python 3.11+ / FastAPI |
| 前端 | 纯 HTML + CSS + JS（无 Node 依赖） |
| 客户端壳 | Tauri 2 (Rust) — 系统 WebView |
| 桌面宠物 | Tauri 透明窗口 + CSS 精灵动画 |
| 数据库 | SQLite（每工作区独立） |
| AI 模型 | DeepSeek / OpenAI / 兼容接口 |
| 包管理 | uv + pyproject.toml (Python) / Cargo (Rust) |

---

## 文件规模硬约束

| 类型 | 限制 |
|------|------|
| Python / HTML / JS / CSS | ≤ 500 行/文件 |

超限时按职责拆分。参考已有工作区的目录结构（如 `workspaces/desktop-pet/`）。

---

## 核心原则

1. **思想基石** — 用户是谁，他想干什么，怎么帮他更好地实现。这三个问题是所有决策的最高准则
2. **AI 主动 > 用户找入口** — 能让 AI 主动推送的信息，不做独立 UI 入口。岛主是主动式管家，不是传统面板软件。堆砌功能 ≠ 产品价值
3. **数据本地化** — 所有数据存储在用户本地，零云端
2. **工作区隔离** — 独立文件夹 + 独立 SQLite + 独立端口
3. **平台不侵入** — 平台层不修改工作区内部代码
4. **文件精简** — 宁可多文件，不可单文件臃肿
5. **开源优先，不造轮子** — 创建工作区时必须先研究开源社区，复用成熟方案
6. **没写完的需求不要标记完成** — 所有 AC 逐条验证通过才能标记 done，避免需求遗漏
7. **完成需求前必须对照 AC 自检** — 实现完后逐条检查 AC，确认代码覆盖了每一条（包括边界 case 和数据持久化），有 AC 未满足的留在 backlog 并标注缺哪条
8. **剃刀原理 — 能改不新建** — 优先修改现有文件/资源，避免无端创建新文件。能用旧图标就不新建 SVG，能改配置就不新增文件
9. **测试文件管理** — 临时测试脚本用完即删，长期测试文件放入 `tests/` 目录，禁止在根目录散落测试文件

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

### 打包规范

**Tauri 打包：**
1. **进程检查** — 确认目标 exe 对应的进程已完全关闭
2. **构建命令** — `cargo tauri build`（在 src-tauri/ 目录下）
3. **产物位置** — `src-tauri/target/release/bundle/`
4. **剃刀原理** — 优先复用现有资源（如 favicon.ico），禁止无端新建文件

**Release 打包安全（🔴 必须遵守）：**
1. **禁止打包任何 `.db` 文件** — 包含用户聊天记录、API Key、待办数据
2. **禁止打包 `.env`** — 包含 API 密钥
3. **禁止打包 `config.json`** — 包含用户配置
4. **验证方法** — 打包后用 zip 工具检查是否有 `.db/.env` 文件，有则立即停止发布
5. **脚本位置** — `scripts/pack_release.py` 中 `_ignore_fn` 负责排除

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

# 开发模式（后端 + 浏览器）
python daozhu_main.py

# Tauri 壳开发（需要 Rust 工具链）
cargo tauri dev                 # 壳 + 后端联调
cargo tauri build               # 正式打包

# 打包发版
python scripts/pack_release.py           # 仅打包 zip
python scripts/publish_release.py v1.0.4 # 打包 + 上传 Gitee Release

# 测试
python tests/run_test.py        # 随机 3 题 agent 准确性测试
python tests/run_test.py --all  # 全部问题
python tests/run_test.py --verify  # 只验真（不调 agent）

# 其他
pytest tests/ -v                # 单元测试
ruff check . && ruff format .   # lint + format
```

---

## 目录结构说明

| 目录/文件 | 用途 |
|-----------|------|
| `daozhu/` | 后端核心代码（FastAPI + Agent） |
| `daozhu/frontend/` | 前端静态文件（HTML/CSS/JS） |
| `daozhu/tools/` | 工具注册和实现 |
| `daozhu/routers/` | FastAPI 路由 |
| `workspaces/` | 各工作区（todo/desktop-pet 等） |
| `scripts/` | 打包发版脚本（pack_release / publish_release） |
| `requirements/` | 需求管理（plan.md + backlog/ + requirements.db） |
| `tests/` | 测试（questions.py 题库 + run_test.py 运行器） |
| `src-tauri/` | Tauri 客户端壳（Rust） |
| `skills/` | AI 技能定义 |
| `logs/` | 运行日志（按日期轮转，.gitignore 已排除） |

---

## Agent 架构（v1.0.4）

```
用户消息
    ↓
[意图识别] agent_intent.py — 分类: simple_chat / needs_action / ambiguous
    ├── simple_chat → 直接对话（不给工具）
    ├── ambiguous → 追问 1 次
    └── needs_action ↓
[规划] agent_planner.py — 生成 goal + steps + fallback
    ↓
[执行循环] agent.py while loop — LLM + tool_calls
    ↓
[目标验证] agent_solver.py — solved_when 满足了吗？
    ├── 未满足 → 注入 fallback hint → 重试 1 次
    └── 满足 ↓
[输出生成] agent_responder.py — 基于 ExecutionRecord 生成回复
    ↓
[事实验证] agent_verifier.py — 代码级比对数字/成功声明
    ↓
最终回复
```

### 关键模块

| 文件 | 职责 | 行数限制 |
|------|------|---------|
| `agent.py` | 主循环入口，消息路由 | ≤ 500 |
| `agent_intent.py` | 意图分类（3 类） | ~90 |
| `agent_planner.py` | 执行计划生成 | ~100 |
| `agent_solver.py` | 目标验证（solved_when） | ~90 |
| `agent_responder.py` | 独立回复生成 | ~80 |
| `agent_verifier.py` | 事实核查（数字/成功声明） | ~100 |
| `agent_guardrails.py` | 循环检测/工具阻断 | ~80 |
| `agent_stream.py` | 流式响应辅助 | ~85 |
| `agent_context.py` | 动态上下文构建 | ~60 |
| `agent_protocol.py` | Anthropic 协议适配 | ~80 |
| `prompts.py` | 所有 prompt 集中管理 | ~110 |

### 意图分类器注意事项

- 接收 `recent_context`（最近 3 轮对话）以理解指代词（"那些"、"这个"）
- 极短消息（≤4 字符常用问候）用规则直接命中，不调 LLM
- 失败时默认 `needs_action`（宁可多给工具，不可漏掉）

---

## 需求管理流程

详见 `requirements/AGENTS.md`。核心流程：

| 状态 | 存储位置 |
|------|---------|
| 待开发 | `requirements/backlog/*.md` + DB 元数据 |
| 已完成 | **仅 DB**（description 字段存完整 md 内容） |
| 已取消 | **仅 DB** |

**完成需求流程：**
1. `UPDATE requirements SET status='done', description='md全文' WHERE id=?`
2. 删除 `backlog/*.md` 文件
3. 更新 `requirements/plan.md`

**发版流程：**
1. 更新 `scripts/pack_release.py` 中 VERSION
2. 更新 `requirements/plan.md` 版本号 + 发布说明
3. `python scripts/publish_release.py v{X.Y.Z}`（自动打包+上传 Gitee）
4. git tag + push --tags

---

## 发版脚本说明

| 脚本 | 用途 |
|------|------|
| `scripts/pack_release.py` | 构建 Tauri exe + 嵌入式 Python + 依赖 → zip |
| `scripts/publish_release.py` | 调用 pack → 创建 Gitee Release → 上传 zip 附件 |

`publish_release.py` 需要 `config.db` 中配置 `GITEE_TOKEN`（通过 app 设置页面配置）。

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
| Tauri JSON 配置有 BOM | 用 `UTF8Encoding($false)` 写文件，不要用 PowerShell `Set-Content` |
| Tauri window.open 无效 | 前端覆盖 `window.open`，调用 Rust IPC `open_external` |
| Tauri 透明窗口有边框 | `.shadow(false)` + `.decorations(false)` |
| Cargo 下载超时 | 配置 `HTTP_PROXY` / `HTTPS_PROXY` 环境变量 |
| SQLite WAL 锁（工作区打不开） | 强杀进程后 `.db-shm/.db-wal` 残留导致锁冲突。删掉这两个文件即可恢复 |
| Clash 代理导致本地连接 502 | `app.py` 顶部 `os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")`；Tauri 用 `.no_proxy()` |
| 🔴 **打包泄露用户数据** | `pack_release.py` 必须用 `_ignore_fn` 排除所有 `.db`/`.env`/`config.json`。`shutil.copytree` 默认复制一切！ |
| 前端 JS 缓存（Tauri WebView） | 每次改 JS/CSS 后必须在 index.html 里升版本号（`?v=N`），或清除 WebView2 缓存 |
| AI 对已上传文件调 read_file | 消息中明确标注"已解析，无需再用工具读取"，SYSTEM_PROMPT 加禁止规则 |

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
