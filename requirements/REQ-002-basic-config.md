# REQ-002 基础配置

**状态：** ✔️ Done  
**优先级：** P0（所有财务功能的前置依赖）  
**T-Shirt Size：** M - 数据模型明确，但科目体系和辅助核算的灵活性设计有复杂度

---

## 问题陈述

财务系统的所有操作都依赖基础配置：账套信息、会计科目体系、辅助核算属性、会计期间等。不同企业的配置差异大，需要支持灵活定制，同时提供合理的默认值让用户快速上手。

## 用户故事

**As a** 用户  
**I want** 通过对话告诉 AI 我的公司类型和行业  
**So that** AI 自动帮我初始化一套适合的会计科目和配置，我不需要手动一个个设置

## 范围

### In Scope

- **用户角色识别** — 首次使用时引导用户选择角色（小企业负责人/专业会计/代账公司员工），决定 AI 交互风格和功能侧重
- **账套管理** — 创建/切换/删除账套，每个账套独立数据库文件（`accounting_{company_id}.db`）
- **代账模式** — 代账公司员工支持管理多家企业账套，有统一的 `master.db` 管理账套元信息
- **会计科目体系** — 预置科目模板（小企业会计准则/企业会计准则），支持自定义增删改
- **科目属性** — 科目编码、名称、类别（资产/负债/权益/成本/损益）、余额方向（借/贷）、是否末级、状态（启用/停用）
- **辅助核算属性** — 部门、客户、供应商、项目、员工、自定义维度
- **币种管理** — 本位币设置、外币币种、汇率
- **会计期间** — 自然年度/非自然年度，期间开启/关闭
- **税率配置** — 常用税率预置（13%/9%/6%/3%/0%），支持自定义

### Out of Scope

- 多租户权限隔离（第四阶段）
- 准则间自动转换

## 文件存储结构

每个账套对应一个独立文件夹，用户可通过 Web UI 按钮直接打开：

```
~/.accobot/data/
├── master.db                          # 全局元信息
├── company_{id}/                      # 每家公司一个文件夹
│   ├── accounting.db                  # 账务数据库
│   ├── documents/                     # 原始单据（发票、收据、银行回单等）
│   │   ├── 2026-01/                   # 按会计期间分文件夹
│   │   ├── 2026-02/
│   │   ├── 2026-03/
│   │   └── ...
│   └── exports/                       # 导出文件（报表等）
```

Web UI 侧边栏账套区域提供"打开文件夹"按钮，点击后用系统文件管理器打开对应公司文件夹。

## 验收标准

1. **AC-1：角色引导** — 首次启动时，Agent 引导用户选择角色（小企业负责人/专业会计/代账公司员工），后续交互风格和功能展示据此调整
2. **AC-2：快速建账** — 用户说"帮我建一个餐饮行业小规模纳税人的账套"，Agent 能自动创建账套并加载对应科目模板，整个过程不超过 3 轮对话
3. **AC-3：科目模板** — 系统预置至少"小企业会计准则"和"企业会计准则"两套科目模板，包含一级到末级科目
4. **AC-4：辅助核算** — 支持为科目挂接辅助核算属性（如：管理费用-差旅费 挂"部门"+"员工"），录入凭证时自动提示填写
5. **AC-5：会计期间** — 支持按月自动生成会计期间，支持期间的开启和关闭操作
6. **AC-6：多账套隔离** — 不同账套的数据完全隔离（独立数据库文件），切换账套后所有查询只返回当前账套数据
7. **AC-7：配置可修改** — 已创建的科目/辅助核算属性可以修改，但已被凭证引用的科目不允许删除（给出提示）
8. **AC-8：代账批量管理** — 代账角色可查看所有管理的账套列表，快速切换，支持跨账套的汇总视图（如：本月哪些公司还没报税）
9. **AC-9：打开文件夹** — 账套区域有"打开文件夹"按钮，点击后用系统文件管理器打开该账套的数据文件夹（包含数据库和原始单据）
10. **AC-10：原始单据文件夹结构** — 创建账套时自动按会计期间建立原始单据存放文件夹（如 `documents/2026-01/`），上传的原始单据自动归入对应期间文件夹
11. **AC-11：删除账套二次确认** — 删除账套时弹出第一次确认（"确定要删除XX公司的账套吗？"），确认后弹出第二次确认（"删除后数据不可恢复，请输入公司名称确认"），两次确认通过后才执行删除

## 数据模型草案

```
~/.accobot/data/                       # 数据根目录
├── master.db                          # 全局元信息数据库
│
├── company_{id}/                      # 每家公司独立文件夹
│   ├── accounting.db                  # 该公司的账务数据库
│   ├── documents/                     # 原始单据存放（发票、收据、银行回单等）
│   │   ├── 2026-01/                   # 按会计期间（年-月）分文件夹
│   │   ├── 2026-02/
│   │   └── ...
│   └── exports/                       # 导出文件（报表PDF/Excel等）

master.db 表结构：
├── user_profile（用户信息）
│   ├── id TEXT PK
│   ├── role TEXT           -- boss/accountant/agency
│   ├── name TEXT
│   └── preferences TEXT    -- AI 交互偏好（JSON）
│
├── companies（账套列表）
│   ├── id TEXT PK
│   ├── name TEXT           -- 公司名称
│   ├── industry TEXT       -- 行业
│   ├── taxpayer_type TEXT  -- general/small_scale
│   ├── accounting_standard TEXT -- small_enterprise/enterprise
│   ├── folder_path TEXT    -- 公司文件夹路径
│   ├── created_at REAL
│   └── status TEXT         -- active/archived

accounting.db 表结构（每家公司独立）：
├── accounts（科目表）
│   ├── code TEXT PK
│   ├── name TEXT
│   ├── category TEXT       -- asset/liability/equity/cost/income/expense
│   ├── balance_direction TEXT -- debit/credit
│   ├── parent_code TEXT
│   ├── is_leaf BOOLEAN
│   ├── is_active BOOLEAN
│   ├── aux_attributes TEXT -- JSON数组
│   └── extra TEXT          -- JSON
│
├── aux_items（辅助核算项目）
│   ├── id TEXT PK
│   ├── type TEXT           -- department/customer/supplier/project/employee/custom
│   ├── code TEXT
│   ├── name TEXT
│   └── extra TEXT          -- JSON
│
├── periods（会计期间）
│   ├── id TEXT PK
│   ├── year INTEGER
│   ├── month INTEGER
│   ├── start_date TEXT
│   ├── end_date TEXT
│   └── status TEXT         -- open/closed
```

## 依赖

- REQ-001（Agent 核心框架）
- SQLite 数据库

## 参考

- 小企业会计准则科目表（财会〔2011〕17号）
- 企业会计准则科目表（财会〔2006〕18号）
