"""
岛主 DaoZhu — 一键发布脚本
用法: python scripts/publish_release.py [版本号]
示例: python scripts/publish_release.py v1.0.1

流程:
1. 运行 pack_release.py 生成 zip
2. 创建 Gitee Release + 上传附件

前置条件:
- config.db 中已配置 GITEE_TOKEN
- Rust 工具链已安装（cargo build --release）
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


def step_pack(version: str) -> Path:
    """打包 release zip"""
    print(f"\n{'='*50}")
    print(f"  Step 1: 打包 release zip")
    print(f"{'='*50}")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "pack_release.py")],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print("  FAILED")
        sys.exit(1)

    # 查找产物
    zip_path = ROOT / "release" / f"岛主DaoZhu-{version}-win-x64.zip"
    if not zip_path.exists():
        print(f"  zip not found: {zip_path}")
        sys.exit(1)
    return zip_path


def step_gitee_release(version: str, zip_path: Path):
    """发布到 Gitee"""
    print(f"\n{'='*50}")
    print(f"  Step 2: 发布到 Gitee")
    print(f"{'='*50}")

    token = get_secret("GITEE_TOKEN")
    if not token:
        print("  未配置 GITEE_TOKEN，跳过")
        return

    base = f"https://gitee.com/api/v5/repos/{OWNER_GITEE}/{REPO_GITEE}"
    body = f"""## 岛主 DaoZhu {version}

### 使用方法
1. 下载 `岛主DaoZhu-{version}-win-x64.zip`
2. 解压到任意目录
3. 双击 `岛主DaoZhu.exe`
4. 首次运行按引导配置 API Key

### 快捷操作
- 关闭窗口 = 最小化到托盘（右下角）
- Ctrl+Alt+D = 全局呼出/隐藏
- 双击桌面宠物 = 呼出主窗口
- 右键托盘 = 菜单

### 系统要求
- Windows 10+ (Edge WebView2 已预装)
"""

    # 检查是否已存在
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
        print(f"  创建失败: {resp.status_code} {resp.text[:200]}")
        return

    release_id = resp.json()["id"]
    print(f"  Release 创建成功 (id={release_id})")

    # 上传附件
    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"  上传 {zip_path.name} ({size_mb:.1f}MB)...")
    with open(zip_path, "rb") as f:
        upload_resp = httpx.post(
            f"{base}/releases/{release_id}/attach_files",
            data={"access_token": token},
            files={"file": (zip_path.name, f, "application/zip")},
            timeout=600,
        )

    if upload_resp.status_code in (200, 201):
        url = upload_resp.json().get("browser_download_url", "")
        print(f"  发布成功!")
        print(f"  下载: {url}")
    else:
        print(f"  上传失败: {upload_resp.status_code} {upload_resp.text[:200]}")


def main():
    version = get_version()
    print(f"\n  岛主 DaoZhu 发布 — {version}")

    zip_path = step_pack(version)
    step_gitee_release(version, zip_path)

    print(f"\n  Done! https://gitee.com/{OWNER_GITEE}/{REPO_GITEE}/releases/tag/{version}\n")


if __name__ == "__main__":
    main()
