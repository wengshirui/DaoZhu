"""
岛主 DaoZhu — 发布脚本
用法: python scripts/publish_release.py [版本号]
示例: python scripts/publish_release.py v0.3.1

流程:
1. 打包 exe (PyInstaller)
2. 压缩为 zip
3. 创建 Gitee Release + 上传附件
4. (可选) 创建 GitHub Release + 上传附件

前置条件:
- config.db 中已配置 GITEE_TOKEN
- (可选) config.db 中配置 GITHUB_TOKEN
- 已安装 pyinstaller: uv pip install pyinstaller
"""

import sys
import subprocess
from pathlib import Path

# 确保能 import daozhu 模块
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import json
import zipfile
import httpx
from daozhu.config_db import get_secret


OWNER_GITEE = "yumen2278"
REPO_GITEE = "DaoZhu"
OWNER_GITHUB = "wengshirui"
REPO_GITHUB = "DaoZhu"


def get_version():
    """从命令行参数或 pyproject.toml 获取版本号"""
    if len(sys.argv) > 1:
        return sys.argv[1]
    # 从 pyproject.toml 读取
    toml = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for line in toml.split("\n"):
        if line.startswith("version"):
            return "v" + line.split('"')[1]
    return "v0.0.0"


def step_build():
    """Step 1: PyInstaller 打包"""
    print("\n" + "=" * 50)
    print("📦 Step 1: PyInstaller 打包")
    print("=" * 50)
    result = subprocess.run(
        [sys.executable, str(ROOT / "build_exe.py")],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print("❌ 打包失败！")
        sys.exit(1)
    print("✅ 打包完成")


def step_zip(version: str) -> Path:
    """Step 2: 压缩为 zip"""
    print("\n" + "=" * 50)
    print("📦 Step 2: 压缩 zip")
    print("=" * 50)

    dist_dir = ROOT / "dist" / "daozhu"
    zip_name = f"daozhu-{version}-win64.zip"
    zip_path = ROOT / "dist" / zip_name

    # 删除旧 zip
    if zip_path.exists():
        zip_path.unlink()

    # 压缩（保留顶层 daozhu/ 目录）
    # 重要：用户解压后应该得到 daozhu/ 文件夹，里面有 daozhu.exe + _internal/
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in dist_dir.rglob("*"):
            if file.is_file():
                arcname = "daozhu/" + str(file.relative_to(dist_dir))
                zf.write(file, arcname)

    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"✅ 压缩完成: {zip_name} ({size_mb:.1f} MB)")
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

    body = f"""## 岛主 DaoZhu {version}

### 使用方式
1. 下载 `daozhu-{version}-win64.zip`
2. 解压到英文路径（如 `D:\\daozhu\\`）
3. 双击 `daozhu\\daozhu.exe`
4. 浏览器自动打开，按引导配置

### ⚠️ 注意
- 必须**完整解压**后再运行，不要在 zip 里直接双击
- 解压路径不要有中文或空格
"""

    # 创建 Release
    resp = httpx.post(
        f"https://gitee.com/api/v5/repos/{OWNER_GITEE}/{REPO_GITEE}/releases",
        json={
            "access_token": token,
            "tag_name": version,
            "target_commitish": "main",
            "name": f"岛主 DaoZhu {version}",
            "body": body,
            "prerelease": False,
        },
        timeout=30,
    )

    if resp.status_code in (200, 201):
        release_id = resp.json()["id"]
        print(f"✅ Release 创建成功 (id={release_id})")
    elif resp.status_code in (400, 422):
        # 已存在，删除后重建
        print("⚠️ Release 已存在，删除后重建...")
        r2 = httpx.get(
            f"https://gitee.com/api/v5/repos/{OWNER_GITEE}/{REPO_GITEE}/releases/tags/{version}",
            params={"access_token": token}, timeout=15,
        )
        if r2.status_code == 200:
            old_id = r2.json()["id"]
            httpx.delete(
                f"https://gitee.com/api/v5/repos/{OWNER_GITEE}/{REPO_GITEE}/releases/{old_id}",
                params={"access_token": token}, timeout=15,
            )
        # 重新创建
        resp2 = httpx.post(
            f"https://gitee.com/api/v5/repos/{OWNER_GITEE}/{REPO_GITEE}/releases",
            json={
                "access_token": token,
                "tag_name": version,
                "target_commitish": "main",
                "name": f"岛主 DaoZhu {version}",
                "body": body,
                "prerelease": False,
            },
            timeout=30,
        )
        if resp2.status_code in (200, 201):
            release_id = resp2.json()["id"]
            print(f"✅ 重建成功 (id={release_id})")
        else:
            print(f"❌ 重建失败: {resp2.status_code} {resp2.text[:200]}")
            return
    else:
        print(f"❌ 创建失败: {resp.status_code} {resp.text[:200]}")
        return

    # 上传附件
    print(f"📤 上传 {zip_path.name}...")
    with open(zip_path, "rb") as f:
        upload_resp = httpx.post(
            f"https://gitee.com/api/v5/repos/{OWNER_GITEE}/{REPO_GITEE}/releases/{release_id}/attach_files",
            data={"access_token": token},
            files={"file": (zip_path.name, f, "application/zip")},
            timeout=300,
        )

    if upload_resp.status_code in (200, 201):
        url = upload_resp.json().get("browser_download_url", "")
        print(f"✅ Gitee 发布成功！")
        print(f"📥 下载: {url}")
    else:
        print(f"❌ 上传失败: {upload_resp.status_code}")


def step_github_release(version: str, zip_path: Path):
    """Step 4: 发布到 GitHub（可选）"""
    print("\n" + "=" * 50)
    print("🚀 Step 4: 发布到 GitHub")
    print("=" * 50)

    token = get_secret("GITHUB_TOKEN")
    if not token:
        print("⚠️ 未配置 GITHUB_TOKEN，跳过 GitHub 发布")
        print("   配置方法: 在设置页面添加 GITHUB_TOKEN")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    # 创建 Release
    resp = httpx.post(
        f"https://api.github.com/repos/{OWNER_GITHUB}/{REPO_GITHUB}/releases",
        headers=headers,
        json={
            "tag_name": version,
            "name": f"岛主 DaoZhu {version}",
            "body": f"See Gitee release for details: https://gitee.com/{OWNER_GITEE}/{REPO_GITEE}/releases/tag/{version}",
            "draft": False,
            "prerelease": False,
        },
        timeout=30,
    )

    if resp.status_code in (200, 201):
        release = resp.json()
        upload_url = release["upload_url"].replace("{?name,label}", "")
        print(f"✅ GitHub Release 创建成功")
    else:
        print(f"❌ GitHub Release 创建失败: {resp.status_code}")
        return

    # 上传附件
    print(f"📤 上传到 GitHub...")
    with open(zip_path, "rb") as f:
        upload_resp = httpx.post(
            f"{upload_url}?name={zip_path.name}",
            headers={**headers, "Content-Type": "application/zip"},
            content=f.read(),
            timeout=300,
        )

    if upload_resp.status_code in (200, 201):
        print(f"✅ GitHub 发布成功！")
    else:
        print(f"❌ GitHub 上传失败: {upload_resp.status_code}")


def main():
    version = get_version()
    print(f"🏝️ 岛主 DaoZhu 发布流程 — {version}")

    step_build()
    zip_path = step_zip(version)
    step_gitee_release(version, zip_path)
    step_github_release(version, zip_path)

    print("\n" + "=" * 50)
    print(f"🎉 发布完成！版本: {version}")
    print("=" * 50)


if __name__ == "__main__":
    main()
