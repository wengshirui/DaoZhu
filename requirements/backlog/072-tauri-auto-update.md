# 072 — 客户端自动更新（Tauri Updater）

> 状态: 🆕 待开发
> 优先级: P1
> T-shirt Size: S
> 录入日期: 2026-06-04

---

## 问题陈述

当前岛主客户端已从旧方案（launcher.py + git pull）迁移到 Tauri 壳，但失去了自动更新能力。
用户需要手动下载新版 zip 覆盖旧文件才能更新，体验差、容易出错。

## 用户故事

**As a** 岛主用户
**I want** 客户端在有新版本时自动提示并一键更新
**So that** 我无需手动下载 zip，始终使用最新功能和修复

## 范围

### In Scope

- 启动时静默检查 Gitee Release 是否有新版本
- 有新版本时弹出系统通知或窗口内提示
- 用户确认后自动下载并替换（或提供下载链接）
- 版本号比对逻辑（语义化版本）

### Out of Scope

- 后台静默更新（不打扰用户）
- 增量更新（delta patch）
- macOS/Linux 自动更新（初期仅 Windows）

## 验收标准

1. **AC1**: 启动时自动检查 Gitee Release 最新版本号，与当前版本比对
2. **AC2**: 有新版本时，托盘通知或主窗口内显示"发现新版本 vX.Y.Z，点击更新"
3. **AC3**: 用户点击更新后，在系统浏览器中打开 Release 下载页面（MVP 方案）
4. **AC4**: 无网络或检查失败时静默跳过，不影响正常使用

## 技术方向

**方案选择（待开发时确认）：**
- **A. Tauri plugin-updater**：官方方案，需要配置 updater endpoint
- **B. 简单 HTTP 检查**：Rust 侧启动时 GET Gitee API 检查版本，提示用户手动下载
- **C. 混合**：先用 B（快速上线），后续迁移到 A

## T-Shirt Size

**S** — 核心逻辑简单（HTTP 请求 + 版本比对 + 通知），无复杂依赖。

## 依赖

- Gitee Release 已配置（✅ 已有）
- 版本号写在 tauri.conf.json 中（✅ 已有）
