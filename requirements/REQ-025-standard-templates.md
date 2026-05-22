# REQ-025 会计准则完整配置（科目/凭证模板/报表规则）

**状态：** 📝 Draft  
**优先级：** L  
**来源：** 2026-05-22 用户需求

---

## 问题陈述

当前准则配置分散在代码中（templates.py 的科目表、standards.py 的规则文档）。需要在项目中建立统一的准则配置目录，每种准则一个文件夹，下面按类别组织科目表、凭证模板、报表规则等配置文件。Agent 做账和生成报表时从这些配置中读取，而非硬编码。

核心原则：**默认即最佳实践**——大多数用户无需自定义，按多数情况执行即可。

## 目录结构

```
accobot/standards/
├── small_enterprise/                    # 小企业会计准则
│   ├── README.md                        # 准则概述、适用范围、核心规则、Agent约束
│   ├── accounts/
│   │   └── chart_of_accounts.json       # 标准科目表
│   ├── vouchers/
│   │   ├── README.md                    # 凭证模板使用说明
│   │   ├── income.json                  # 收入类模板（收货款、收服务费...）
│   │   ├── expense.json                 # 支出类模板（付房租、水电费...）
│   │   ├── salary.json                  # 薪酬类模板（发工资、交社保...）
│   │   ├── tax.json                     # 税费类模板（交增值税、附加税...）
│   │   └── period_end.json             # 期末类模板（结转损益、折旧...）
│   ├── reports/
│   │   ├── README.md                    # 报表规则说明
│   │   ├── profit_loss.json             # 利润表取数规则
│   │   └── balance_sheet.json           # 资产负债表取数规则
│   ├── tax/
│   │   ├── README.md                    # 税务要求说明
│   │   ├── vat_rules.json              # 增值税规则（税率、免征条件、申报周期）
│   │   ├── income_tax_rules.json       # 企业所得税规则（预缴、汇算清缴）
│   │   └── surcharge_rules.json        # 附加税规则（减半政策等）
│   └── audit/
│       ├── README.md                    # 审计要求说明
│       └── checklist.json              # 审计检查清单（小企业简化审计要求）
│
├── enterprise/                          # 企业会计准则
│   ├── README.md
│   ├── accounts/
│   │   └── chart_of_accounts.json
│   ├── vouchers/
│   │   ├── README.md
│   │   ├── income.json
│   │   ├── expense.json
│   │   ├── salary.json
│   │   ├── tax.json
│   │   ├── period_end.json
│   │   └── impairment.json             # 减值类模板（企业准则特有）
│   ├── reports/
│   │   ├── README.md
│   │   ├── profit_loss.json
│   │   └── balance_sheet.json
│   ├── tax/
│   │   ├── README.md
│   │   ├── vat_rules.json              # 增值税规则（一般纳税人进项抵扣等）
│   │   ├── income_tax_rules.json       # 企业所得税规则（纳税调整项）
│   │   └── surcharge_rules.json
│   └── audit/
│       ├── README.md                    # 审计要求说明
│       ├── checklist.json              # 审计检查清单（完整审计要求）
│       └── disclosure.json             # 披露要求（附注披露事项）
│
└── __init__.py                          # 加载器：按准则名称读取配置
```

## 文件格式规范

### README.md（准则概述）

包含：准则全称、适用范围、核心规则差异、Agent 做账约束（禁用科目等）。

### vouchers/*.json（凭证模板）

```json
[
  {
    "id": "income_goods",
    "name": "销售商品收款",
    "keywords": ["收货款", "销售收入", "卖货", "收到货款"],
    "entries": [
      {"account_code": "1002", "direction": "debit", "description": "银行存款"},
      {"account_code": "5001", "direction": "credit", "description": "主营业务收入"}
    ],
    "note": "金额由用户提供，如涉及增值税需拆分税额"
  }
]
```

### reports/*.json（报表取数规则）

```json
{
  "name": "利润表",
  "items": [
    {
      "row": 1,
      "name": "一、营业收入",
      "formula": "credit_balance(5001) + credit_balance(5051)",
      "accounts": ["5001", "5051"]
    },
    {
      "row": 2,
      "name": "减：营业成本",
      "formula": "debit_balance(5401) + debit_balance(5402)",
      "accounts": ["5401", "5402"]
    }
  ]
}
```

## 范围

**In Scope:**
- 项目中建立上述目录结构
- 预置小企业会计准则和企业会计准则的完整配置
- 凭证模板：每套准则至少 15 个常见业务场景
- 报表规则：利润表 + 资产负债表的完整取数规则
- 加载器：按准则名称读取对应目录下的配置文件
- Agent 做账时优先匹配凭证模板，匹配失败回退模型推理
- 报表生成时使用取数规则计算

**Out of Scope:**
- 用户自定义准则配置 UI
- 现金流量表
- 合并报表
- 国际会计准则（IFRS）

## 用户故事

As a 小微企业老板，I want Agent 遇到常见业务时直接按标准模板记账，报表按准则规则自动生成，so that 我不需要每次都解释业务细节，记账更快更准确。

## 验收标准

1. **AC-1 目录结构**：项目中存在 `accobot/standards/{准则名}/` 目录，包含 README.md、accounts/、vouchers/、reports/ 子目录
2. **AC-2 凭证模板预置**：每套准则至少 15 个凭证模板，覆盖收入、支出、薪酬、税费、期末结转等场景
3. **AC-3 报表取数规则**：利润表和资产负债表每个项目有明确的取数公式，按准则区分
4. **AC-4 模板匹配**：Agent 生成分录时优先匹配凭证模板，匹配失败回退模型推理
5. **AC-5 报表使用规则**：报表生成读取 reports/*.json 计算，而非硬编码
6. **AC-6 默认无需配置**：用户选择准则后对应模板和规则自动生效

## 业务价值

- 提升记账准确率：模板匹配比纯推理更可靠（~85% → ~95%）
- 提升记账速度：模板匹配无需多轮推理
- 报表准确性：取数规则确保数字与凭证一致
- 可维护性：准则配置集中管理，新增准则只需加目录

## T-Shirt Size

**L** - 需要建立目录结构、预置 30+ 模板文件、实现匹配引擎、设计取数规则、改造报表生成；风险在于模板覆盖度和匹配准确率

## 依赖与约束

- 依赖 REQ-023（准则基础设施——需迁移到新目录结构）
- 依赖 REQ-004（做账流程）
- 依赖 REQ-008（报表生成）
- 约束：模板匹配失败必须优雅回退
- 约束：预置模板基于中国大陆小微企业最常见业务场景
