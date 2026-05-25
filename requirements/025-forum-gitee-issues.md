# REQ-025: 岛主论坛 — 对接 Gitee Issues

> Intake ID: 2025-05-25-forum-gitee-issues
> 优先级: 🟡 中（用户反馈渠道，验证产品价值）

---

## 问题陈述

岛主论坛工作区目前是空壳。需要对接 Gitee 项目的 Issues 作为论坛服务，用户可以在岛主内直接浏览、提问、回复 Issue，同时本地 data.db 缓存内容。

## 用户故事

**As a** 岛主用户，
**I want** 在论坛工作区直接浏览和参与 Gitee Issues 讨论，
**so that** 我不需要离开岛主就能反馈问题和交流经验。

## 功能设计

1. **浏览 Issues** — 从 Gitee API 拉取 issue 列表，展示标题/状态/回复数
2. **查看详情** — 点击 issue 查看正文和评论
3. **发表评论** — 用户登录 Gitee 后可回复（OAuth 或 Token）
4. **创建 Issue** — 用户可在岛主内提交新问题
5. **本地缓存** — data.db 存储 issue 内容，离线可浏览历史

## 前提条件

- 用户需要有 Gitee 账号
- 需要配置 Gitee Personal Access Token
- 引导页中增加 Gitee Token 配置步骤

## 验收标准

| # | AC | 可测试性 |
|---|-----|----------|
| 1 | 论坛工作区启动后展示 gitee.com/yumen2278/DaoZhu 的 Issues 列表 | 打开论坛验证 |
| 2 | 点击 Issue 显示正文和评论内容 | 点击验证 |
| 3 | 配置 Gitee Token 后可发表评论 | 发表后 Gitee 上可见 |
| 4 | 无网络时显示本地缓存的历史 Issue | 断网后验证 |
| 5 | 未配置 Token 时，浏览可用但发表提示"请先配置 Gitee 账号" | 未配置时验证 |

## T-Shirt Size

**M (5 pts)** — Gitee API 集成 + OAuth/Token + 本地缓存 + 前端展示

## 依赖

- Gitee Open API: https://gitee.com/api/v5
- 项目仓库: yumen2278/DaoZhu

---
