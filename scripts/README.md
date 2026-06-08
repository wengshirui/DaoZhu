# 构建与发布

## ⚠️ 安全警告

> **打包时绝对不能包含用户个人数据！**
>
> 以下文件在 `pack_release.py` 中通过 `_ignore_fn` 自动排除：
> - 所有 `.db` 文件（聊天记录、待办数据、用户画像等）
> - `.env`（API Key 等密钥）
> - `config.json`（用户配置）
>
> **发布前必须验证：** 用 zip 工具打开产物，搜索 `.db` 和 `.env`，确认为零。

---

## 打包 Release

```bash
# 打包 Windows portable zip
python scripts/pack_release.py

# 产物: release/岛主DaoZhu-v{version}-win-x64.zip
```

## 发布到 Gitee

```bash
# 打包 + 上传到 Gitee Release
python scripts/publish_release.py v1.0.2
```

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `pack_release.py` | 生成 portable zip（Tauri exe + 嵌入式 Python + 源码） |
| `publish_release.py` | pack + 上传到 Gitee Release |

## 前置条件

- Rust 工具链（`rustup`、`cargo`）
- Python 3.11+ + uv
- `config.db` 中配置 `GITEE_TOKEN`（发布用）

## Release 包结构

```
岛主DaoZhu/
├── 岛主DaoZhu.exe     (Tauri 壳, ~13MB)
├── python/            (嵌入式 Python + 依赖)
├── daozhu/            (后端源码 + 前端)
├── workspaces/        (工作区代码，不含 data.db)
├── skills/            (AI 技能)
└── README.txt         (使用说明)
```

**不包含：** `.db`、`.env`、`config.json`、`__pycache__`、`.git`
