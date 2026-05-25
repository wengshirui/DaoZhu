"""
岛主 DaoZhu — 打包入口
PyInstaller 打包时使用此文件作为入口点
"""

import sys
import webbrowser
import threading
from pathlib import Path

# 确保能找到模块
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的路径
    BASE_DIR = Path(sys._MEIPASS)
    # 设置工作目录为 exe 所在目录（用户数据存这里）
    import os
    os.chdir(Path(sys.executable).parent)
else:
    BASE_DIR = Path(__file__).parent


def main():
    import uvicorn
    from daozhu.app import app
    from daozhu.config import get_config_value

    port = get_config_value("platform.port", 7788)
    host = "127.0.0.1"

    # 1.5 秒后自动打开浏览器
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open(f"http://{host}:{port}")

    threading.Thread(target=open_browser, daemon=True).start()

    print(f"\n  🏝️ 岛主 DaoZhu 已启动")
    print(f"  📍 http://{host}:{port}")
    print(f"  按 Ctrl+C 退出\n")

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
