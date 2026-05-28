"""
岛主 DaoZhu — 轻量启动器
打包为 exe 后，用户双击即可：
1. 使用自带的 Git + uv（vendor/ 目录）
2. 自动更新源码（git pull）
3. 同步依赖（uv sync）
4. 启动服务

无需用户安装任何东西，零网络依赖（除了 git pull 和首次装 Python）。
"""

import subprocess
import sys
import os
import webbrowser
import time
import threading
from pathlib import Path

# 项目根目录 = exe 所在目录（或脚本所在目录）
if getattr(sys, 'frozen', False):
    ROOT = Path(sys.executable).parent
else:
    ROOT = Path(__file__).parent

# vendor 目录下的本地工具
VENDOR_DIR = ROOT / "vendor"
VENDOR_GIT = VENDOR_DIR / "git" / "cmd" / "git.exe"
VENDOR_UV = VENDOR_DIR / "uv" / "uv.exe"

# Git 仓库地址（公开仓库，无需认证）
GIT_REMOTE = "https://gitee.com/yumen2278/DaoZhu.git"


# === 输出 ===
def info(msg): print(f"  ℹ️  {msg}")
def ok(msg): print(f"  ✅ {msg}")
def warn(msg): print(f"  ⚠️  {msg}")
def err(msg): print(f"  ❌ {msg}")


# === 工具路径解析 ===
def get_git():
    """获取 git 可执行文件路径（优先 vendor）"""
    if VENDOR_GIT.exists():
        return str(VENDOR_GIT)
    # 回退到系统 PATH
    import shutil
    sys_git = shutil.which("git")
    if sys_git:
        return sys_git
    return None


def get_uv():
    """获取 uv 可执行文件路径（优先 vendor）"""
    if VENDOR_UV.exists():
        return str(VENDOR_UV)
    # 回退到系统 PATH
    import shutil
    sys_uv = shutil.which("uv")
    if sys_uv:
        return sys_uv
    return None


def run_cmd(cmd, cwd=None, check=True, capture=True, timeout=180):
    """执行命令，返回 (成功, stdout)"""
    try:
        result = subprocess.run(
            cmd, cwd=cwd or ROOT, shell=True,
            capture_output=capture, text=True, timeout=timeout,
        )
        if check and result.returncode != 0:
            return False, result.stderr or result.stdout
        return True, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "命令超时"
    except FileNotFoundError:
        return False, "命令未找到"


# === 环境检测 ===
def check_tools():
    """检测 Git 和 uv 是否可用"""
    git = get_git()
    uv = get_uv()

    if git:
        ok_r, ver = run_cmd(f'"{git}" --version')
        if ok_r:
            ok(f"Git: {ver}")
    else:
        err("Git 未找到！请将 vendor/git/ 放在项目目录下")
        return False

    if uv:
        ok_r, ver = run_cmd(f'"{uv}" --version')
        if ok_r:
            ok(f"uv: {ver}")
    else:
        err("uv 未找到！请将 vendor/uv/ 放在项目目录下")
        return False

    return True


# === Git 操作 ===
def is_git_repo():
    """检测当前目录是否是 git 仓库"""
    return (ROOT / ".git").is_dir()


def git_pull():
    """拉取最新代码"""
    git = get_git()

    if not is_git_repo():
        info("首次运行，正在克隆项目...")
        ok_r, output = run_cmd(f'"{git}" clone {GIT_REMOTE} .', cwd=ROOT)
        if not ok_r:
            err(f"克隆失败: {output}")
            return False
        ok("项目克隆完成")
        return True

    info("检查更新...")
    ok_r, _ = run_cmd(f'"{git}" fetch origin', cwd=ROOT)
    if not ok_r:
        warn("无法连接远程仓库，使用本地版本")
        return False

    # 对比本地和远程 hash
    ok_r, local_hash = run_cmd(f'"{git}" rev-parse HEAD', cwd=ROOT)
    ok_r2, remote_hash = run_cmd(f'"{git}" rev-parse origin/main', cwd=ROOT)

    if ok_r and ok_r2 and local_hash == remote_hash:
        ok("已是最新版本")
        return True

    # 有更新
    info("发现新版本，正在更新...")
    run_cmd(f'"{git}" stash', cwd=ROOT)
    ok_r, output = run_cmd(f'"{git}" pull origin main --ff-only', cwd=ROOT)
    if not ok_r:
        warn("快进合并失败，强制更新...")
        run_cmd(f'"{git}" reset --hard origin/main', cwd=ROOT)
    ok("更新完成")
    return True


# === 依赖同步 ===
def sync_deps():
    """同步 Python 依赖"""
    uv = get_uv()
    venv_dir = ROOT / ".venv"

    if not venv_dir.exists():
        info("创建虚拟环境...")
        run_cmd(f'"{uv}" venv .venv --python 3.11', cwd=ROOT, timeout=300)

    info("同步依赖...")
    ok_r, output = run_cmd(f'"{uv}" pip install -e .', cwd=ROOT, timeout=300)
    if ok_r:
        ok("依赖同步完成")
    else:
        warn(f"依赖同步可能有问题: {output[:200]}")


# === 启动服务 ===
def get_version():
    """从 pyproject.toml 读取版本号"""
    toml_path = ROOT / "pyproject.toml"
    if toml_path.exists():
        for line in toml_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("version"):
                return line.split('"')[1]
    return "unknown"


def start_service():
    """启动岛主服务"""
    version = get_version()
    print(f"\n  🏝️  岛主 DaoZhu v{version}")
    print(f"  📍 http://127.0.0.1:7788")
    print(f"  按 Ctrl+C 退出\n")

    # 1.5 秒后打开浏览器
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:7788")
    threading.Thread(target=open_browser, daemon=True).start()

    # 用 .venv 中的 python 启动
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        cmd = f'"{venv_python}" -m daozhu_main'
    else:
        uv = get_uv()
        cmd = f'"{uv}" run daozhu'

    try:
        subprocess.run(cmd, cwd=ROOT, shell=True)
    except KeyboardInterrupt:
        print("\n  👋 再见！")


# === 主入口 ===
def main():
    print("\n" + "=" * 50)
    print("  🏝️  岛主 DaoZhu — 启动器")
    print("=" * 50 + "\n")

    # 1. 检测本地工具
    info("检测运行环境...")
    if not check_tools():
        input("\n按回车键退出...")
        return

    # 2. 更新源码
    git_pull()

    # 3. 同步依赖
    sync_deps()

    # 4. 启动服务
    start_service()


if __name__ == "__main__":
    main()
