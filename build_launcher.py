"""
岛主 DaoZhu — 启动器打包脚本
只打包 launcher.py 为一个极小的 exe（~10MB）
用户双击 exe → 自动检测环境 → 更新源码 → 启动服务
"""

import PyInstaller.__main__
from pathlib import Path

ROOT = Path(__file__).parent


def build():
    """打包启动器"""
    PyInstaller.__main__.run([
        str(ROOT / "launcher.py"),
        "--name=岛主DaoZhu",
        "--onefile",          # 单文件 exe
        "--console",          # 保留控制台（显示启动日志）
        # 图标
        f"--icon={ROOT / 'daozhu' / 'frontend' / 'favicon.ico'}",
        # 输出目录
        f"--distpath={ROOT / 'dist'}",
        f"--workpath={ROOT / 'build'}",
        "--clean",
        "--noconfirm",
    ])

    print(f"\n✅ 启动器打包完成！")
    print(f"   输出: dist/岛主DaoZhu.exe")
    print(f"\n📦 分发方式:")
    print(f"   1. 将 dist/岛主DaoZhu.exe 放入项目根目录")
    print(f"   2. 用户双击 exe 即可自动安装环境 + 更新 + 启动")
    print(f"   3. 或者将整个项目打成 zip，exe 在根目录")


if __name__ == "__main__":
    build()
