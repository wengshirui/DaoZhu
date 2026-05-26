"""
Gitee API 客户端
对接 https://gitee.com/api/v5
"""

import json
import os
from typing import Optional

import httpx

OWNER = "yumen2278"
REPO = "DaoZhu"
BASE_URL = "https://gitee.com/api/v5"


def _get_token() -> Optional[str]:
    """获取 Gitee Token"""
    # 方案1: 直接从主平台 config_db 导入（轻挂载时可用）
    try:
        from daozhu.config_db import get_secret
        val = get_secret("GITEE_TOKEN")
        if val:
            return val
    except ImportError:
        pass

    # 方案2: 直接读 config.db 文件
    try:
        import sqlite3
        from pathlib import Path
        for db_path in [
            Path(__file__).parent.parent.parent / "config.db",
            Path("config.db"),
        ]:
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT value FROM config WHERE key = 'GITEE_TOKEN'").fetchone()
                conn.close()
                if row:
                    return row["value"]
    except Exception:
        pass

    # 方案3: 环境变量
    return os.environ.get("GITEE_TOKEN")


async def fetch_issues(state: str = "open", page: int = 1, per_page: int = 20) -> list[dict]:
    """获取 Issues 列表"""
    params = {"state": state, "page": page, "per_page": per_page, "sort": "updated"}
    token = _get_token()
    if token:
        params["access_token"] = token

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{BASE_URL}/repos/{OWNER}/{REPO}/issues", params=params)
        if resp.status_code != 200:
            return []
        return resp.json()


async def fetch_issue_comments(number: int) -> list[dict]:
    """获取 Issue 的评论"""
    params = {"page": 1, "per_page": 50}
    token = _get_token()
    if token:
        params["access_token"] = token

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{BASE_URL}/repos/{OWNER}/{REPO}/issues/{number}/comments",
            params=params,
        )
        if resp.status_code != 200:
            return []
        return resp.json()


async def create_comment(number: int, body: str) -> Optional[dict]:
    """发表评论（需要 Token）"""
    token = _get_token()
    if not token:
        return None

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{BASE_URL}/repos/{OWNER}/{REPO}/issues/{number}/comments",
            json={"access_token": token, "body": body},
        )
        if resp.status_code in (200, 201):
            return resp.json()
        return None


async def create_issue(title: str, body: str = "") -> Optional[dict]:
    """创建 Issue（需要 Token）"""
    token = _get_token()
    if not token:
        return None

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{BASE_URL}/repos/{OWNER}/{REPO}/issues",
            json={"access_token": token, "title": title, "body": body, "repo": REPO},
        )
        if resp.status_code in (200, 201):
            return resp.json()
        return None
