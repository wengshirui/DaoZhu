"""
岛主 DaoZhu — 开发调试入口
直接运行此文件启动后端服务，浏览器打开 http://localhost:7788
"""

import webbrowser
import threading
import time

import uvicorn


def open_browser(port: int):
    """等待服务就绪后自动打开浏览器"""
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{port}")


def main():
    from daozhu.config import get_config_value

    port = get_config_value("platform.port", 7788)
    host = "127.0.0.1"

    print(f"\n  🏝️  岛主 DaoZhu — 开发模式")
    print(f"  http://{host}:{port}")
    print(f"  按 Ctrl+C 退出\n")

    # 自动打开浏览器
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    uvicorn.run(
        "daozhu.app:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=["daozhu"],
    )


if __name__ == "__main__":
    main()
