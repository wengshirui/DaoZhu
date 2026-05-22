# REQ-021 Spec: 凭证事后质检自动触发

## Story 1: 质检引擎提取 + 结果持久化

**User Story:** As a 系统，I want 将质检逻辑提取为独立可调用的引擎函数，并将结果持久化到数据库，so that 质检可以在任何时机被自动触发且结果可追溯。

**Story Points:** 3

### Acceptance Criteria

- AC-1: 质检引擎函数 `run_quality_check(voucher_id)` 可独立调用，返回结构化结果（pass/fail + issues 列表）
- AC-2: 数据库新增 `quality_checks` 表，记录每次质检的凭证ID、时间、结果、问题列表
- AC-3: 质检规则至少包含：借贷平衡、科目余额方向异常、大额现金（>5万）、空摘要、无分录
- AC-4: 质检执行时间 < 100ms（单张凭证）

### Design

**数据库 Schema 变更：**

```sql
CREATE TABLE IF NOT EXISTS quality_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_id TEXT NOT NULL REFERENCES vouchers(id),
    checked_at REAL NOT NULL,
    passed INTEGER NOT NULL DEFAULT 0,
    issues TEXT NOT NULL DEFAULT '[]',
    extra TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_qc_voucher ON quality_checks(voucher_id);
```

**质检引擎接口：**

```python
# accobot/tools/quality_engine.py

@dataclass
class QualityIssue:
    level: str       # "critical" | "warning" | "info"
    rule: str        # 规则标识，如 "balance_check"
    message: str     # 用户可读消息（通俗语言）
    
@dataclass
class QualityResult:
    passed: bool
    issues: List[QualityIssue]
    checked_at: float

def run_quality_check(voucher_id: str, db: AccountingDB) -> QualityResult:
    """对单张凭证执行质检，返回结构化结果。"""
    ...

def save_quality_result(voucher_id: str, result: QualityResult, db: AccountingDB) -> int:
    """持久化质检结果到数据库。"""
    ...
```

### Tasks

**Task 1.1: 创建 quality_engine.py 模块**
- 从 `quality_check_tool.py` 提取单凭证质检逻辑为 `run_quality_check()`
- 定义 `QualityIssue` 和 `QualityResult` 数据类
- 质检消息使用通俗语言（如"这笔分录借方和贷方金额不相等"）
- 预计工时：0.5 天

**Task 1.2: 数据库 schema 升级 + 持久化**
- 在 `AccountingDB._init_schema()` 中添加 `quality_checks` 表
- 实现 `save_quality_result()` 和 `get_quality_result(voucher_id)` 方法
- 预计工时：0.5 天

---

## Story 2: 过账前自动质检拦截

**User Story:** As a 小微企业老板，I want 凭证过账前系统自动检查有没有问题，so that 错误的凭证不会被写入正式账簿。

**Story Points:** 2

### Acceptance Criteria

- AC-1: `create_voucher_with_entries()` 在过账前自动调用质检，critical 级别问题阻止过账
- AC-2: `post_voucher()` 在过账前自动调用质检，critical 级别问题阻止过账
- AC-3: 质检不通过时返回错误信息，包含具体问题描述和修正建议
- AC-4: warning 级别问题不阻止过账，但在返回消息中提示用户
- AC-5: 原有 `check_vouchers` 工具改为调用新引擎（保持向后兼容）

### Design

**改造 voucher_tool.py：**

```python
# create_voucher_with_entries() 中，过账前插入：
from accobot.tools.quality_engine import run_quality_check, save_quality_result

qc_result = run_quality_check(voucher_id, db)
save_quality_result(voucher_id, qc_result, db)

if not qc_result.passed:
    # 有 critical 问题，不过账，保持 draft 状态
    critical_msgs = [i.message for i in qc_result.issues if i.level == "critical"]
    return tool_error(f"质检不通过，凭证保持草稿状态：\n" + "\n".join(critical_msgs))

# warning 级别：过账但提示
warnings = [i.message for i in qc_result.issues if i.level == "warning"]
db.update_voucher_status(voucher_id, "posted")
if warnings:
    msg += "\n⚠️ 提示：" + "；".join(warnings)
```

**改造 quality_check_tool.py：**

```python
# check_vouchers() 改为调用 quality_engine
from accobot.tools.quality_engine import run_quality_check

for v in vouchers:
    result = run_quality_check(v["id"], db)
    # ... 格式化输出（保持原有输出格式）
```

### Tasks

**Task 2.1: 改造 voucher_tool.py 过账流程**
- 在 `create_voucher_with_entries()` 过账前调用 `run_quality_check()`
- 在 `post_voucher()` 过账前调用 `run_quality_check()`
- critical → 阻止过账 + 返回错误；warning → 过账 + 附带提示
- 预计工时：0.5 天

**Task 2.2: 改造 quality_check_tool.py 使用新引擎**
- `check_vouchers()` 内部改为调用 `run_quality_check()`
- 保持原有的输出格式和注册 schema 不变
- 预计工时：0.5 天

---

## 实施顺序

1. Story 1 → Story 2（Story 2 依赖 Story 1 的引擎模块）

## 风险

- 低风险：`create_voucher_with_entries()` 当前是自动过账，加入质检后如果 critical 不通过会变成 draft 状态——Agent 需要知道如何处理这种情况（修正后重新过账）
- 缓解：在错误消息中明确告知"请修正后使用 post_voucher 重新过账"
