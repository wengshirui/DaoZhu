# 068 — 工作区分类（system / public / user）

> 状态: 🆕 待开发
> 优先级: P1
> T-shirt Size: S
> 录入日期: 2026-06-03

---

## 问题陈述

当前所有工作区平铺在侧边栏，没有分类。随着工作区数量增长（系统内置的、社区公开的、
用户私有的），全部混在一起越来越难找。

需要引入三级分类：
- **system** — 系统自带的，对平台运行和成长有用（定时任务、Agent 复盘、桌面宠物）
- **public** — 公开/社区的（论坛、资讯、市场分享的工作区）
- **user** — 用户私有的（待办、记账、人际关系管理等）

## 用户故事

**As a** 岛主用户
**I want** 工作区按用途分类展示
**So that** 我能快速找到想用的工作区，系统工作区不干扰日常使用

## 范围

### In Scope

- workspace.json 新增 `category` 字段：`system` / `public` / `user`（默认 `user`）
- 侧边栏按分类分组展示（可折叠的分组标题）
- 系统工作区默认折叠（不占空间，需要时展开）
- 已有工作区自动归类：桌面宠物→system，论坛→public，其余→user

### Out of Scope

- 用户自定义分类名
- 分类间拖拽移动
- 分类的增删改管理界面

## 验收标准

1. **AC1**: workspace.json 支持 `category` 字段，新建工作区时可指定分类
2. **AC2**: 侧边栏按 system / public / user 三组展示，每组有标题
3. **AC3**: 没有 `category` 字段的旧工作区默认归为 `user`
4. **AC4**: system 分组默认折叠，点击标题可展开/收起
5. **AC5**: `mode: bound`（绑定文件夹）的工作区默认归为 `user`

## 业务价值

- 侧边栏不再混乱（用户工作区 vs 系统工作区分开）
- 为后续工作区市场（#066-C）的"公开"分类打基础
- 系统工作区不干扰用户日常操作（默认折叠）

## T-Shirt Size

**S** — workspace.json 加一个字段 + 侧边栏渲染逻辑分组 + 默认值兼容；
无 schema 变更，无新 API。

## 依赖

- workspace_manager.py（WorkspaceInfo 加 category 字段）
- sidebar.js（按 category 分组渲染）
