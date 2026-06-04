"""
岛主 DaoZhu — PySide6 混合架构打包脚本
打包 daozhu_main.py 为 exe，包含 QWebEngineView 支持
用户双击 exe → 启动 PySide6 窗口 + uvicorn 后台服务
"""

import PyInstaller.__main__
from pathlib import Path

ROOT = Path(__file__).parent.parent


def build():
    """打包岛主主程序（PySide6 + WebEngine）"""
    print("🔨 开始打包岛主 DaoZhu (PySide6 混合架构)...")
    
    PyInstaller.__main__.run([
        str(ROOT / "daozhu_main.py"),
        "--name=岛主DaoZhu",
        "--onefile",          # 单文件 exe
        "--windowed",         # 无控制台窗口（GUI 应用）
        # 图标
        f"--icon={ROOT / 'daozhu' / 'frontend' / 'favicon.ico'}",
        # 输出目录
        f"--distpath={ROOT / 'dist'}",
        f"--workpath={ROOT / 'build'}",
        "--clean",
        "--noconfirm",
        
        # === 关键：包含 PySide6 WebEngine 模块 ===
        "--hidden-import=PySide6.QtWebEngineWidgets",
        "--hidden-import=PySide6.QtWebEngineCore",
        "--hidden-import=PySide6.QtWebChannel",
        
        # === 收集 PySide6 资源文件 ===
        "--collect-all=PySide6",
        
        # === 排除不必要的模块（减小体积）===
        "--exclude-module=PySide6.QtDesigner",
        "--exclude-module=PySide6.QtHelp",
        "--exclude-module=PySide6.QtLocation",
        "--exclude-module=PySide6.QtMultimedia",
        "--exclude-module=PySide6.QtMultimediaWidgets",
        "--exclude-module=PySide6.QtPositioning",
        "--exclude-module=PySide6.QtQuick",
        "--exclude-module=PySide6.QtQuickWidgets",
        "--exclude-module=PySide6.QtSensors",
        "--exclude-module=PySide6.QtSerialPort",
        "--exclude-module=PySide6.QtSql",
        "--exclude-module=PySide6.QtTest",
        "--exclude-module=PySide6.QtXml",
        
        # === 包含前端静态文件 ===
        f"--add-data={ROOT / 'daozhu' / 'frontend'};daozhu/frontend",
    ])

    print(f"\n✅ 打包完成！")
    print(f"   输出: dist/岛主DaoZhu.exe")
    print(f"\n⚠️  注意:")
    print(f"   - 首次运行需要 .venv 环境和依赖")
    print(f"   - 建议配合 launcher.py 使用（自动安装环境）")
    print(f"   - 或直接分发整个项目文件夹")


if __name__ == "__main__":
    build()
