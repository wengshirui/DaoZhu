# 报表取数规则说明

本目录包含小企业会计准则下的报表取数规则。

## 取数公式说明

- `credit_balance(code)`: 该科目的贷方余额（收入/负债/权益类）
- `debit_balance(code)`: 该科目的借方余额（资产/费用类）
- `credit_occur(code)`: 该科目本期贷方发生额
- `debit_occur(code)`: 该科目本期借方发生额
- 支持通配符：`5601*` 表示 5601 及其所有子科目

## 文件

- `profit_loss.json` — 利润表
- `balance_sheet.json` — 资产负债表
