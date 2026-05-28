"""
岛主 DaoZhu — 一键发布脚本（v1.0+ 新方案）
用法: python scripts/publish_release.py [版本号]
示例: python scripts/publish_release.py v1.0.0

流程:
1. 打包启动器 exe (PyInstaller)
2. 压缩为 zip（exe + 源码 + vendor）
3. 创建 Gitee Release + 上传附件

前置条件:
- config.db 中已配置 GITEE_TOKEN
- vendor/git/ 和 vendor/uv/ 已准备好
- 已安装 pyinstaller + httpx
"""

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import httpx
from daozhu.config_db import get_secret

OWNER_GITEE = "yumen2278"
REPO_GITEE = "DaoZhu"


def get_version():
    """从命令行参数或 pyproject.toml 获取版本号"""
    if len(sys.argv) > 1:
        v = sys.argv[1]
        return v if v.startswith("v") else f"v{v}"
    toml = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for line in toml.split("\n"):
        if line.startswith("version"):
            return "v" + line.split('"')[1]
    return "v0.0.0"


def step_build_launcher():
    """Step 1: 打包启动器 exe"""
    print("\n" + "=" * 50)
    print("📦 Step 1: 打包启动器 exe")
    print("=" * 50)
    result = subprocess.run(
        [sys.executable, str(ROOT / "build_launcher.py")],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print("❌ 打包失败！")
        sys.exit(1)


def step_pack_zip(version: str) -> Path:
    """Step 2: 打包分发 zip"""
    print("\n" + "=" * 50)
    print("📦 Step 2: 打包分发 zip")
    print("=" * 50)
    result = subprocess.run(
        [sys.executable, str(ROOT / "pack_release.py")],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print("❌ 打包 zip 失败！")
        sys.exit(1)

    zip_path = ROOT / "dist" / f"DaoZhu-{version}.zip"
    if not zip_path.exists():
        print(f"❌ zip 文件不存在: {zip_path}")
        sys.exit(1)
    return zip_path


def step_gitee_release(version: str, zip_path: Path):
    """Step 3: 发布到 Gitee"""
    print("\n" + "=" * 50)
    print("🚀 Step 3: 发布到 Gitee")
    print("=" * 50)

    token = get_secret("GITEE_TOKEN")
    if not token:
        print("⚠️ 未配置 GITEE_TOKEN，跳过 Gitee 发布")
        return

    base = f"https://gitee.com/api/v5/repos/{OWNER_GITEE}/{REPO_GITEE}"
    body = f"""## 岛主 DaoZhu {version}

### 使用方式
1. 下载 `DaoZhu-{version}.zip`
2. 解压到任意目录
3. 双击 `岛主DaoZhu.exe`
4. 首次运行自动创建环境并安装依赖
5. 后续每次启动自动检查更新（git pull）

### 包含内容
- 岛主DaoZhu.exe — 启动器
- vendor/git/ — 便携版 Git
- vendor/uv/ — Python 包管理器
- 项目源码
"""

    # 检查是否已存在，存在则删除
    r = httpx.get(f"{base}/releases/tags/{version}",
                  params={"access_token": token}, timeout=15)
    if r.status_code == 200:
        old_id = r.json()["id"]
        print(f"  删除旧 Release (id={old_id})...")
        httpx.delete(f"{base}/releases/{old_id}",
                     params={"access_token": token}, timeout=15)

    # 创建 Release
    resp = httpx.post(f"{base}/releases", json={
        "access_token": token,
        "tag_name": version,
        "target_commitish": "main",
        "name": f"岛主 DaoZhu {version}",
        "body": body,
    }, timeout=30)

    if resp.status_code not in (200, 201):
        print(f"❌ 创建失败: {resp.status_code} {resp.text[:200]}")
        return

    release_id = resp.json()["id"]
    print(f"✅ Release 创建成功 (id={release_id})")

    # 上传附件
    print(f"📤 上传 {zip_path.name} ({zip_path.stat().st_size/1024/1024:.1f}MB)...")
    with open(zip_path, "rb") as f:
        upload_resp = httpx.post(
            f"{base}/releases/{release_id}/attach_files",
            data={"access_token": token},
            files={"file": (zip_path.name, f, "application/zip")},
            timeout=300,
        )

    if upload_resp.status_code in (200, 201):
        url = upload_resp.json().get("browser_download_url", "")
        print(f"✅ 发布成功！")
        print(f"📥 下载: {url}")
    else:
        print(f"❌ 上传失败: {upload_resp.status_code} {upload_resp.text[:200]}")


def main():
    version = get_version()
    print(f"🏝️ 岛主 DaoZhu 发布流程 — {version}")

    step_build_launcher()
    zip_path = step_pack_zip(version)
    step_gitee_release(version, zip_path)

    print("\n" + "=" * 50)
    print(f"🎉 发布完成！版本: {version}")
    print(f"   https://gitee.com/{OWNER_GITEE}/{REPO_GITEE}/releases/tag/{version}")
    print("=" * 50)


if __name__ == "__main__":
    main()
