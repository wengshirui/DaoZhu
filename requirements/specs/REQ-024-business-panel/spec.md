# REQ-024 Spec: 业务操作区（数据浏览与筛选）

## Story 1: 后端 API 补充（凭证/账簿查询）

**Story Points:** 2

### Tasks
- Task 1.1: 新增 `/api/vouchers` 凭证列表 API（支持日期/状态/关键字筛选）
- Task 1.2: 新增 `/api/vouchers/{id}` 凭证详情 API
- Task 1.3: 新增 `/api/ledger/balance-sheet` 科目余额表 API

## Story 2: 前端业务操作区改造

**Story Points:** 3

### Tasks
- Task 2.1: 左侧面板改造——待办移到顶部通知栏，面板改为业务导航+数据区
- Task 2.2: 实现凭证列表+筛选+详情展开
- Task 2.3: 实现科目列表+账簿余额表浏览
