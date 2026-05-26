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
    try:
        from daozhu.config_db import get_secret
        return get_secret("GITEE_TOKEN")
    except Exception:
        pass
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
            f"{BASE_URL}/repos/{OWNER}/issues",
            json={"access_token": token, "title": title, "body": body, "repo": REPO},
        )
        if resp.status_code in (200, 201):
            return resp.json()
        # 返回错误信息而非 None，让前端显示具体原因
        return {"error": f"Gitee API: {resp.status_code} {resp.text[:100]}"}
