"""
岛主 DaoZhu — Release 打包脚本
生成 portable zip 包，用户解压即用。

用法: python scripts/pack_release.py

产物: release/岛主DaoZhu-v{version}-win-x64.zip
"""

import os
import sys
import shutil
import subprocess
import zipfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
VERSION = "1.0.4"
PYTHON_VERSION = "3.11.9"
PYTHON_EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"

RELEASE_DIR = ROOT / "release"
BUNDLE_DIR = RELEASE_DIR / "岛主DaoZhu"
TAURI_EXE = ROOT / "src-tauri" / "target" / "release" / "daozhu.exe"


def step(msg):
    print(f"\n{'='*50}")
    print(f"  {msg}")
    print(f"{'='*50}")


def build_tauri():
    """构建 Tauri release exe"""
    step("1. 构建 Tauri 客户端壳")
    if TAURI_EXE.exists():
        print(f"  已存在: {TAURI_EXE} ({TAURI_EXE.stat().st_size // 1024 // 1024} MB)")
        return

    env = os.environ.copy()
    cargo_bin = Path.home() / ".cargo" / "bin"
    env["PATH"] = f"{cargo_bin};{env['PATH']}"

    result = subprocess.run(
        ["cargo", "build", "--release"],
        cwd=ROOT / "src-tauri",
        env=env,
    )
    if result.returncode != 0:
        print("  ❌ Tauri 构建失败")
        sys.exit(1)
    print(f"  ✓ 构建完成: {TAURI_EXE.stat().st_size // 1024 // 1024} MB")


def download_python_embed():
    """下载 Python 嵌入式发行版"""
    step("2. 准备嵌入式 Python")
    embed_zip = RELEASE_DIR / f"python-{PYTHON_VERSION}-embed-amd64.zip"
    python_dir = BUNDLE_DIR / "python"

    if python_dir.exists() and (python_dir / "python.exe").exists():
        print("  已存在，跳过下载")
        return

    python_dir.mkdir(parents=True, exist_ok=True)

    if not embed_zip.exists():
        print(f"  下载: {PYTHON_EMBED_URL}")
        urllib.request.urlretrieve(PYTHON_EMBED_URL, embed_zip)
        print(f"  ✓ 下载完成: {embed_zip.stat().st_size // 1024} KB")

    # 解压
    import zipfile as zf
    with zf.ZipFile(embed_zip, 'r') as z:
        z.extractall(python_dir)
    print(f"  ✓ 解压到: {python_dir}")

    # 启用 pip: 修改 python311._pth 文件，取消 import site 注释
    pth_files = list(python_dir.glob("python*._pth"))
    for pth in pth_files:
        content = pth.read_text(encoding="utf-8")
        content = content.replace("#import site", "import site")
        pth.write_text(content, encoding="utf-8")
        print(f"  ✓ 启用 site-packages: {pth.name}")


def install_dependencies():
    """在嵌入式 Python 中安装项目依赖"""
    step("3. 安装 Python 依赖")
    python_exe = BUNDLE_DIR / "python" / "python.exe"

    if not python_exe.exists():
        print("  ❌ Python 未就绪")
        sys.exit(1)

    # 先安装 pip
    get_pip = RELEASE_DIR / "get-pip.py"
    if not get_pip.exists():
        print("  下载 get-pip.py...")
        urllib.request.urlretrieve(
            "https://bootstrap.pypa.io/get-pip.py", get_pip
        )

    # 检查 pip 是否已安装
    result = subprocess.run(
        [str(python_exe), "-m", "pip", "--version"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("  安装 pip...")
        subprocess.run([str(python_exe), str(get_pip)], check=True)

    # 安装项目依赖（排除开发依赖）
    print("  安装项目依赖...")
    subprocess.run([
        str(python_exe), "-m", "pip", "install",
        "--no-warn-script-location",
        "-r", str(ROOT / "requirements-release.txt"),
    ], check=True)
    print("  ✓ 依赖安装完成")


def assemble_bundle():
    """组装发布包"""
    step("4. 组装发布包")
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

    # 敏感/用户数据排除列表
    EXCLUDE_PATTERNS = {
        ".env", "chat.db", "config.db", "memory.db", "growth.db",
        "scheduler.db", "idle_work.db", "data.db", "prd.db",
        ".window_state.json", "config.json",
    }
    EXCLUDE_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "target", "logs"}

    def _ignore_fn(directory, files):
        """shutil.copytree ignore 回调：排除敏感文件和目录"""
        ignored = set()
        for f in files:
            if f in EXCLUDE_PATTERNS:
                ignored.add(f)
            if f.endswith(".db"):
                ignored.add(f)
            if f in EXCLUDE_DIRS:
                ignored.add(f)
        return ignored

    # 复制 Tauri exe
    dest_exe = BUNDLE_DIR / "岛主DaoZhu.exe"
    shutil.copy2(TAURI_EXE, dest_exe)
    print(f"  ✓ 客户端壳: {dest_exe.name}")

    # 复制 Python 源码
    daozhu_dest = BUNDLE_DIR / "daozhu"
    if daozhu_dest.exists():
        shutil.rmtree(daozhu_dest)
    shutil.copytree(ROOT / "daozhu", daozhu_dest, ignore=_ignore_fn)
    print(f"  ✓ 后端源码: daozhu/")

    # 复制工作区（排除用户数据）
    ws_dest = BUNDLE_DIR / "workspaces"
    if ws_dest.exists():
        shutil.rmtree(ws_dest)
    shutil.copytree(ROOT / "workspaces", ws_dest, ignore=_ignore_fn)
    print(f"  ✓ 工作区: workspaces/")

    # 复制技能
    skills_src = ROOT / "skills"
    if skills_src.exists():
        skills_dest = BUNDLE_DIR / "skills"
        if skills_dest.exists():
            shutil.rmtree(skills_dest)
        shutil.copytree(skills_src, skills_dest, ignore=_ignore_fn)
        print(f"  ✓ 技能: skills/")

    # 确保不复制根目录的敏感文件
    for sensitive in EXCLUDE_PATTERNS:
        p = BUNDLE_DIR / sensitive
        if p.exists():
            p.unlink()

    # 生成 README.txt
    write_readme()
    print(f"  ✓ README.txt")


def write_readme():
    """生成用户使用说明"""
    readme = BUNDLE_DIR / "README.txt"
    readme.write_text("""\
═══════════════════════════════════════
  🏝️  岛主 DaoZhu — 你的 AI 数字小岛
═══════════════════════════════════════

【使用方法】
  双击 "岛主DaoZhu.exe" 即可运行。

【首次运行】
  会弹出引导页面，请输入 DeepSeek API Key。
  (获取地址: https://platform.deepseek.com)

【快捷操作】
  - 关闭窗口    → 最小化到系统托盘（右下角）
  - 双击托盘    → 重新打开窗口
  - 右键托盘    → 显示菜单 / 退出
  - Ctrl+Alt+D  → 全局呼出/隐藏窗口
  - 双击桌面宠物 → 呼出主窗口
  - 拖拽宠物    → 移动宠物（会跑动）

【系统要求】
  - Windows 10 (1803+) 或 Windows 11
  - 已安装 Microsoft Edge WebView2 Runtime
    (Windows 10/11 通常已预装，如未安装请访问:
     https://developer.microsoft.com/edge/webview2)

【常见问题】
  Q: 启动后加载中很久？
  A: 首次启动需等待 Python 后端初始化（3-5 秒）。

  Q: 提示端口占用？
  A: 修改 config.json 中的 "platform.port" 值。

  Q: 宠物没有出现？
  A: 确认 workspaces/desktop-pet/pets/ 目录下有宠物资源。
     右键托盘图标 → "显示/隐藏宠物"。

  Q: 找不到托盘图标？
  A: 点击任务栏右下角的 "^" 展开隐藏图标。

【版本】v""" + VERSION + """
【开源】https://gitee.com/yumen2278/DaoZhu
""", encoding="utf-8")


def create_zip():
    """压缩为最终 zip"""
    step("5. 创建 zip 压缩包")
    zip_name = f"岛主DaoZhu-v{VERSION}-win-x64.zip"
    zip_path = RELEASE_DIR / zip_name

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in BUNDLE_DIR.rglob('*'):
            if file.is_file():
                arcname = f"岛主DaoZhu/{file.relative_to(BUNDLE_DIR)}"
                zf.write(file, arcname)

    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"\n  ✅ 打包完成!")
    print(f"  📦 {zip_path}")
    print(f"  📏 {size_mb:.1f} MB")


def main():
    print("\n  岛主 DaoZhu — Release 打包")
    print(f"  版本: v{VERSION}")
    print(f"  目标: Windows x64 portable zip\n")

    build_tauri()
    download_python_embed()
    install_dependencies()
    assemble_bundle()
    create_zip()

    print("\n  Done! 可以发布了。\n")


if __name__ == "__main__":
    main()
