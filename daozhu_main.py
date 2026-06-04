"""
岛主 DaoZhu — 开发调试入口

用法:
  python daozhu_main.py          # 启动后端 + 浏览器（开发模式）
  python daozhu_main.py --shell  # 启动后端 + Tauri 客户端壳
"""

import sys
import os
import subprocess
import webbrowser
import threading
import time
from pathlib import Path

ROOT = Path(__file__).parent


def start_shell():
    """启动 Tauri 客户端壳（清缓存 + 杀旧进程 + 启动 exe）"""
    import shutil

    # 杀掉旧进程
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/IM", "daozhu.exe"],
            capture_output=True,
        )
        time.sleep(1)

    # 清 WebView2 缓存
    cache_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "com.daozhu.app"
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)

    # 查找 exe
    exe_path = ROOT / "src-tauri" / "target" / "debug" / "daozhu.exe"
    if not exe_path.exists():
        exe_path = ROOT / "src-tauri" / "target" / "release" / "daozhu.exe"
    if not exe_path.exists():
        print("  ❌ 未找到 daozhu.exe，请先运行: cargo build")
        print(f"     (在 {ROOT / 'src-tauri'} 目录下)")
        sys.exit(1)

    print(f"  🏝️  岛主客户端启动中...")
    print(f"  exe: {exe_path}")
    subprocess.Popen([str(exe_path)], cwd=str(ROOT))
    print(f"  ✓ 已启动\n")


def start_dev():
    """启动后端服务 + 打开浏览器（开发模式）"""
    import uvicorn
    from daozhu.config import get_config_value

    port = get_config_value("platform.port", 7788)
    host = "127.0.0.1"

    print(f"\n  🏝️  岛主 DaoZhu — 开发模式")
    print(f"  http://{host}:{port}")
    print(f"  按 Ctrl+C 退出\n")

    # 自动打开浏览器
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}")

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "daozhu.app:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=["daozhu"],
    )


def main():
    if "--shell" in sys.argv:
        start_shell()
    else:
        start_dev()


if __name__ == "__main__":
    main()
