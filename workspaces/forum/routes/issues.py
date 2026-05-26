"""Issues 路由 — 对接 Gitee + 本地缓存"""

import json
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import get_db
import gitee_client

router = APIRouter()


class CommentCreate(BaseModel):
    body: str


class IssueCreate(BaseModel):
    title: str
    body: str = ""


@router.get("/")
async def list_issues(state: str = "open", page: int = 1):
    """获取 Issues 列表（优先从 Gitee 拉取，失败时用缓存）"""
    try:
        issues = await gitee_client.fetch_issues(state=state, page=page)
        if issues:
            _cache_issues(issues)
            return {"issues": _format_issues(issues), "source": "gitee"}
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Gitee fetch failed: {type(e).__name__}: {e}")

    # 降级：从本地缓存读取
    db = get_db()
    rows = db.execute(
        "SELECT * FROM issues WHERE state = ? ORDER BY updated_at DESC LIMIT 20",
        (state,),
    ).fetchall()
    db.close()
    return {"issues": [dict(r) for r in rows], "source": "cache"}


@router.get("/{number}")
async def get_issue(number: int):
    """获取 Issue 详情 + 评论"""
    try:
        comments = await gitee_client.fetch_issue_comments(number)
        _cache_comments(number, comments)
    except Exception:
        comments = None

    # 从缓存读取 issue
    db = get_db()
    issue = db.execute("SELECT * FROM issues WHERE number = ?", (number,)).fetchone()
    if not issue:
        db.close()
        raise HTTPException(404, "Issue 不存在")

    if comments is None:
        cached = db.execute(
            "SELECT * FROM comments WHERE issue_number = ? ORDER BY created_at",
            (number,),
        ).fetchall()
        comments = [dict(r) for r in cached]
    else:
        comments = _format_comments(comments)

    db.close()
    result = dict(issue)
    result["comments"] = comments
    return result


@router.post("/{number}/comments")
async def add_comment(number: int, data: CommentCreate):
    """发表评论"""
    result = await gitee_client.create_comment(number, data.body)
    if result is None:
        raise HTTPException(403, "请先在主平台设置页面()配置 Gitee Token")
    return {"success": True, "comment": result}


@router.post("/")
async def create_issue(data: IssueCreate):
    """创建新 Issue"""
    result = await gitee_client.create_issue(data.title, data.body)
    if result is None:
        raise HTTPException(403, "请先在主平台设置页面(⚙️)配置 Gitee Token")
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(400, result["error"])
    return {"success": True, "issue": result}


# === 缓存辅助 ===

def _cache_issues(issues: list[dict]):
    """将 Gitee Issues 缓存到本地"""
    db = get_db()
    for issue in issues:
        db.execute(
            """INSERT OR REPLACE INTO issues (id, number, title, body, state, author, labels, comments_count, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                issue.get("id"),
                issue.get("number"),
                issue.get("title", ""),
                issue.get("body", ""),
                issue.get("state", "open"),
                issue.get("user", {}).get("login", ""),
                json.dumps([l.get("name", "") for l in issue.get("labels", [])]),
                issue.get("comments", 0),
                issue.get("created_at", ""),
                issue.get("updated_at", ""),
            ),
        )
    db.commit()
    db.close()


def _cache_comments(issue_number: int, comments: list[dict]):
    """缓存评论"""
    db = get_db()
    for c in comments:
        db.execute(
            """INSERT OR REPLACE INTO comments (id, issue_number, body, author, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                c.get("id"),
                issue_number,
                c.get("body", ""),
                c.get("user", {}).get("login", ""),
                c.get("created_at", ""),
            ),
        )
    db.commit()
    db.close()


def _format_issues(issues: list[dict]) -> list[dict]:
    """格式化 Gitee API 返回的 Issues"""
    return [
        {
            "id": i.get("id"),
            "number": i.get("number"),
            "title": i.get("title", ""),
            "state": i.get("state", "open"),
            "author": i.get("user", {}).get("login", ""),
            "comments_count": i.get("comments", 0),
            "labels": [l.get("name", "") for l in i.get("labels", [])],
            "created_at": i.get("created_at", ""),
            "updated_at": i.get("updated_at", ""),
        }
        for i in issues
    ]


def _format_comments(comments: list[dict]) -> list[dict]:
    """格式化评论"""
    return [
        {
            "id": c.get("id"),
            "body": c.get("body", ""),
            "author": c.get("user", {}).get("login", ""),
            "created_at": c.get("created_at", ""),
        }
        for c in comments
    ]
