"""
岛主 DaoZhu — 打包入口
PyInstaller 打包时使用此文件作为入口点
"""

import sys
import os
import webbrowser
import threading
from pathlib import Path

# PyInstaller 打包环境检测
IS_FROZEN = getattr(sys, 'frozen', False)

# PyInstaller --noconsole 模式下 stdout/stderr 可能为 None 或 GBK 编码
# 统一处理：打包模式下重定向到 devnull，避免 isatty() 崩溃和编码错误
if IS_FROZEN:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

# 确保能找到模块
if IS_FROZEN:
    BASE_DIR = Path(sys._MEIPASS)
    os.chdir(Path(sys.executable).parent)
else:
    BASE_DIR = Path(__file__).parent


def main():
    import uvicorn
    import signal
    import atexit
    from daozhu.app import app
    from daozhu.config import get_config_value
    from daozhu.workspace_manager import manager

    port = get_config_value("platform.port", 7788)
    host = "127.0.0.1"

    # 退出时清理所有子进程
    def cleanup():
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(manager.shutdown())
            loop.close()
        except Exception:
            # 最后手段：强杀所有子进程
            for ws in manager.workspaces.values():
                if ws.process:
                    ws.process.kill()

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda *_: (cleanup(), exit(0)))

    # 1.5 秒后自动打开浏览器
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open(f"http://{host}:{port}")

    threading.Thread(target=open_browser, daemon=True).start()

    if not IS_FROZEN:
        print(f"\n  🏝️ 岛主 DaoZhu 已启动")
        print(f"  📍 http://{host}:{port}")
        print(f"  按 Ctrl+C 退出\n")

    uvicorn.run(app, host=host, port=port, log_level="warning" if IS_FROZEN else "info")


if __name__ == "__main__":
    main()
