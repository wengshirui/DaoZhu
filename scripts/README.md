# 构建与发布

## 打包 Release

```bash
# 打包 Windows portable zip
python scripts/pack_release.py

# 产物: release/岛主DaoZhu-v{version}-win-x64.zip
```

## 发布到 Gitee

```bash
# 打包 + 上传到 Gitee Release
python scripts/publish_release.py v1.0.1
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
├── workspaces/        (工作区 + 默认宠物)
├── skills/            (AI 技能)
└── README.txt         (使用说明)
```
