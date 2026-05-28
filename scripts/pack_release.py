"""
岛主 DaoZhu — 打包分发 zip
生成: dist/DaoZhu-v{version}.zip
内容: 启动器 exe + 项目源码（排除 .venv, .git, __pycache__ 等）
"""

import zipfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent

# 排除的目录和文件
EXCLUDE_DIRS = {
    ".venv", ".git", ".idea", ".vscode", "__pycache__",
    "build", "dist", ".playwright-mcp", "node_modules",
    ".kiro",
}
EXCLUDE_FILES = {
    ".env", "chat.db", "config.db", "memory.db",
    "岛主DaoZhu.spec", "daozhu.spec",
}
EXCLUDE_EXTS = {".pyc", ".pyo", ".db", ".log"}


def get_version():
    with open(ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]


def should_include(path: Path) -> bool:
    """判断文件是否应该包含在 zip 中"""
    # 排除目录
    for part in path.relative_to(ROOT).parts:
        if part in EXCLUDE_DIRS:
            return False
    # 排除文件
    if path.name in EXCLUDE_FILES:
        return False
    # 排除扩展名
    if path.suffix in EXCLUDE_EXTS:
        return False
    return True


def pack():
    version = get_version()
    zip_name = f"DaoZhu-v{version}.zip"
    zip_path = ROOT / "dist" / zip_name
    zip_path.parent.mkdir(exist_ok=True)

    # 确保启动器 exe 存在
    exe_path = ROOT / "dist" / "岛主DaoZhu.exe"
    if not exe_path.exists():
        print("❌ 启动器 exe 不存在，请先运行 build_launcher.py")
        return

    print(f"📦 正在打包 {zip_name} ...")

    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. 放入启动器 exe（在 zip 根目录）
        zf.write(exe_path, "DaoZhu/岛主DaoZhu.exe")
        file_count += 1

        # 2. 放入源码
        for file in sorted(ROOT.rglob("*")):
            if not file.is_file():
                continue
            if not should_include(file):
                continue
            rel = file.relative_to(ROOT)
            zf.write(file, f"DaoZhu/{rel}")
            file_count += 1

    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"\n✅ 打包完成！")
    print(f"   文件: dist/{zip_name}")
    print(f"   大小: {size_mb:.1f} MB")
    print(f"   包含: {file_count} 个文件")
    print(f"\n📋 用户使用方式:")
    print(f"   1. 解压 zip")
    print(f"   2. 双击 岛主DaoZhu.exe")
    print(f"   3. 自动安装环境 + 启动服务")


if __name__ == "__main__":
    pack()
