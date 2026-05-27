# 📦 发布脚本

## 发布流程

```bash
# 1. 确保代码已提交并打 tag
git tag v0.3.2
git push origin main --tags

# 2. 一键发布（打包 + 压缩 + 上传）
python scripts/publish_release.py v0.3.2
```

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `publish_release.py` | 完整发布流程（打包→压缩→Gitee/GitHub Release） |

## 打包踩坑记录

### ❌ 用户报错 "Failed to load Python DLL"

**原因**：zip 压缩方式不对。

| 错误方式 | 正确方式 |
|---------|---------|
| `Compress-Archive -Path dist\daozhu\*` | `zipfile` 保留顶层 `daozhu/` 目录 |
| 用户解压后文件散落 | 用户解压后得到 `daozhu/` 文件夹 |
| `_internal` 路径被截断 | 完整路径 `daozhu/_internal/python311.dll` |

**正确的压缩方式**（publish_release.py 中已实现）：
```python
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for file in dist_dir.rglob("*"):
        if file.is_file():
            arcname = "daozhu/" + str(file.relative_to(dist_dir))
            zf.write(file, arcname)
```

### ❌ PowerShell Compress-Archive 的坑

- `Compress-Archive -Path "dist\daozhu\*"` → 内容散落，无顶层目录
- `Compress-Archive -Path "dist\daozhu"` → 有顶层目录，但某些解压工具处理 `_internal` 异常
- **结论**：用 Python `zipfile` 模块手动控制路径最可靠

### 用户使用注意事项（写在 Release 说明中）

1. 必须**完整解压**后再运行（不要在 zip 里双击）
2. 解压路径不要有中文或空格
3. 运行 `daozhu\daozhu.exe`（不是直接运行 `daozhu.exe`）

## 前置条件

- `config.db` 中配置了 `GITEE_TOKEN`
- (可选) `config.db` 中配置了 `GITHUB_TOKEN`
- 已安装 PyInstaller: `uv pip install pyinstaller`
- 已安装 httpx: `uv pip install httpx`
