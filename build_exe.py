"""
岛主 DaoZhu — PyInstaller 打包脚本
生成单目录 exe，用户双击即可运行
"""

import PyInstaller.__main__
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist" / "daozhu"


def build():
    """执行打包"""
    PyInstaller.__main__.run([
        str(ROOT / "daozhu_main.py"),
        "--name=daozhu",
        "--onedir",
        "--noconsole",
        # 包含数据文件
        f"--add-data={ROOT / 'daozhu' / 'frontend'};daozhu/frontend",
        f"--add-data={ROOT / 'templates'};templates",
        f"--add-data={ROOT / 'skills'};skills",
        f"--add-data={ROOT / 'workspaces'};workspaces",
        # 隐藏导入
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        # 图标
        f"--icon={ROOT / 'daozhu' / 'frontend' / 'favicon.ico'}",
        # 输出目录
        f"--distpath={ROOT / 'dist'}",
        f"--workpath={ROOT / 'build'}",
        "--clean",
        "--noconfirm",
    ])

    print(f"\n✅ 打包完成！输出目录: {DIST}")
    print(f"   运行: dist/daozhu/daozhu.exe")


if __name__ == "__main__":
    build()
