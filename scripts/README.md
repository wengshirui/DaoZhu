# 📦 发布脚本

## 发布流程（v1.0+ 新方案）

```bash
# 1. 确保代码已提交
git add . && git commit -m "feat: xxx"
git push origin main

# 2. 一键发布（打包启动器 → 压缩 → 上传 Gitee Release）
python scripts/publish_release.py v1.0.0
```

## 新方案 vs 旧方案

| | 旧方案（v0.x） | 新方案（v1.0+） |
|--|--|--|
| 打包内容 | 整个项目 + Python 运行时 | 轻量启动器 exe + 源码 + vendor |
| zip 大小 | ~150MB | ~77MB |
| 更新方式 | 重新下载 zip | exe 自动 git pull |
| 用户需安装 | 无 | 无（Git/uv 自带在 vendor/） |

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `publish_release.py` | 完整发布：打包启动器 → 压缩 → Gitee Release |
| `build_launcher.py` | 单独打包启动器 exe |
| `pack_release.py` | 单独打包分发 zip |

## 前置条件

- `config.db` 中配置了 `GITEE_TOKEN`
- `vendor/git/` 和 `vendor/uv/` 已下载（首次需手动准备）
- 已安装 PyInstaller: `uv pip install pyinstaller`
- 已安装 httpx: `uv pip install httpx`

## vendor 目录准备

首次需要下载 MinGit 和 uv 放入 `vendor/`：

```bash
# MinGit (便携版 Git)
# 从 https://github.com/git-for-windows/git/releases 下载 MinGit-*-64-bit.zip
# 解压到 vendor/git/

# uv
# 从 https://github.com/astral-sh/uv/releases 下载 uv-x86_64-pc-windows-msvc.zip
# 解压到 vendor/uv/
```
