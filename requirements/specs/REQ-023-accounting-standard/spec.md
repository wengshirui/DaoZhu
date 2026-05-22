# REQ-023 Spec: 账套会计准则维护

## Story 1: 准则文档生成与存储

**User Story:** As a 系统，I want 账套创建时自动生成准则约束文档到账套目录下，so that Agent 做账时能读取准则规则作为约束。

**Story Points:** 3

### Acceptance Criteria

- AC-1: 账套创建后，在 `company_{id}/standard/` 目录下生成 `accounting_rules.md`（准则规则说明）和 `chart_of_accounts.json`（标准科目表）
- AC-2: `accounting_rules.md` 包含准则名称、适用范围、核心规则（科目使用约束、核算要求）
- AC-3: 支持两种准则：小企业会计准则、企业会计准则
- AC-4: Agent system prompt 动态加载当前账套的准则文档摘要

### Design

**目录结构：**
```
company_{id}/
├── standard/
│   ├── accounting_rules.md    # 准则规则（Agent 读取）
│   └── chart_of_accounts.json # 标准科目表
├── documents/
├── exports/
└── accounting.db
```

**准则文档内容（accounting_rules.md）：**
- 准则名称和适用对象
- 科目使用约束（哪些科目可用/不可用）
- 核算规则（如：小企业准则不要求计提坏账准备）
- 报表要求差异

**Agent 加载方式：**
在 `AccoAgent.__init__` 中，读取当前账套的 `standard/accounting_rules.md`，追加到 system prompt。

### Tasks

**Task 1.1: 创建准则文档模板**
- 在 `accobot/db/` 下新增 `standards.py`，包含两套准则的规则文档内容
- 小企业会计准则：适用小微企业，不要求递延所得税、不要求坏账准备等
- 企业会计准则：完整准则，包含递延所得税、资产减值等
- 预计工时：1 天

**Task 1.2: 账套创建时生成准则文档**
- 改造 `DBManager.create_company()`，创建 `standard/` 目录并写入文档
- 实现 `generate_standard_docs(company_dir, standard_name)` 函数
- 预计工时：0.5 天

**Task 1.3: Agent 动态加载准则**
- 改造 `AccoAgent.__init__`，读取当前账套的准则文档摘要注入 system prompt
- 如果账套未选择则跳过
- 预计工时：0.5 天

---

## Story 2: 企业会计准则科目模板

**User Story:** As a 使用企业会计准则的公司，I want 创建账套时能选择企业会计准则并获得对应的标准科目表，so that 我的科目体系符合准则要求。

**Story Points:** 2

### Acceptance Criteria

- AC-1: `templates.py` 新增企业会计准则科目模板（含递延所得税、资产减值准备等小企业准则没有的科目）
- AC-2: 创建账套时选择 `enterprise` 准则，初始化对应科目表
- AC-3: 两套科目表的共同科目编码保持一致，差异科目有明确区分

### Tasks

**Task 2.1: 编写企业会计准则科目模板**
- 在 `templates.py` 中新增 `ENTERPRISE_ACCOUNTS` 列表
- 包含：递延所得税资产/负债、坏账准备、资产减值损失、公允价值变动损益等
- `load_template("enterprise")` 返回新模板
- 预计工时：1 天

---

## Story 3: 准则切换

**User Story:** As a 企业老板，I want 能切换账套的会计准则（如从小企业升级到企业会计准则），so that 公司规模变化后账务处理能跟上。

**Story Points:** 2

### Acceptance Criteria

- AC-1: 提供 `switch_accounting_standard(company_id, new_standard)` 功能
- AC-2: 切换后重新生成准则文档，不修改已有科目和凭证
- AC-3: 切换时提示用户影响范围
- AC-4: 切换后可能需要补充新准则要求的科目（如企业准则需要"递延所得税"），提示用户

### Tasks

**Task 3.1: 实现准则切换逻辑**
- 新增 config_tool 中的准则切换功能
- 更新 master DB 中的 `accounting_standard` 字段
- 重新生成 `standard/` 目录下的文档
- 提示缺失科目
- 预计工时：0.5 天

---

## 实施顺序

Story 1 → Story 2 → Story 3（线性依赖）
