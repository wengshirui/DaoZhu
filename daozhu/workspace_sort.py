"""
岛主 DaoZhu — 工作区自动排序服务
根据 tool_logs 中近 7 天的使用频率自动优化工作区显示顺序。

使用频率权重：
- call_workspace_api: 3 分/次（直接操作）
- start_workspace: 2 分/次（主动启动）
- get_workspace_info: 1 分/次（查看信息）
"""
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from .config import PLATFORM_ROOT

logger = logging.getLogger(__name__)

# 各工具操作的使用权重
WEIGHTS = {
    "call_workspace_api": 3,
    "start_workspace": 2,
    "get_workspace_info": 1,
}

TOOL_LOG_DB = PLATFORM_ROOT / "tool_log.db"


def _get_workspace_dir() -> Path:
    """获取工作区根目录"""
    from .config import get_workspace_dir as _gwd
    return _gwd()


def _get_workspace_ids() -> list[str]:
    """获取所有工作区 ID"""
    ws_dir = _get_workspace_dir()
    ids = []
    if not ws_dir.exists():
        return ids
    for item in sorted(ws_dir.iterdir()):
        if item.is_dir() and (item / "workspace.json").exists():
            ids.append(item.name)
    return ids


def _read_workspace_json(ws_id: str) -> dict | None:
    """读取工作区的 workspace.json"""
    path = _get_workspace_dir() / ws_id / "workspace.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_workspace_json(ws_id: str, data: dict) -> bool:
    """写回 workspace.json"""
    path = _get_workspace_dir() / ws_id / "workspace.json"
    try:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except OSError as e:
        logger.error("写入 workspace.json 失败 %s: %s", ws_id, e)
        return False


def compute_frequency_scores(days: int = 7) -> dict[str, int]:
    """从 tool_logs 统计各工作区近 N 天的加权使用频率

    Returns:
        {workspace_id: weighted_score}
    """
    import sqlite3

    scores: dict[str, int] = defaultdict(int)
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    if not TOOL_LOG_DB.exists():
        logger.warning("tool_log DB 不存在: %s", TOOL_LOG_DB)
        return dict(scores)

    try:
        conn = sqlite3.connect(str(TOOL_LOG_DB))
        conn.row_factory = sqlite3.Row

        # 查询与工作区相关的工具调用
        tool_names = tuple(WEIGHTS.keys())
        placeholders = ",".join("?" for _ in tool_names)
        rows = conn.execute(
            f"""SELECT tool_name, args
                FROM tool_logs
                WHERE tool_name IN ({placeholders})
                  AND created_at > ?
                ORDER BY id""",
            (*tool_names, cutoff),
        ).fetchall()
        conn.close()

        for row in rows:
            tool_name = row["tool_name"]
            weight = WEIGHTS.get(tool_name, 1)
            try:
                args = json.loads(row["args"]) if row["args"] else {}
            except json.JSONDecodeError:
                continue

            ws_id = args.get("workspace_id")
            if ws_id:
                scores[ws_id] += weight

        return dict(scores)

    except sqlite3.Error as e:
        logger.error("查询 tool_logs 失败: %s", e)
        return {}


def auto_sort_workspaces(days: int = 7) -> dict:
    """执行工作区自动排序

    Returns:
        {
            "changed": bool,          # 是否有排序变更
            "new_order": list[str],   # 新排序（workspace_id 列表）
            "scores": dict,           # {workspace_id: score}
            "message": str,           # 日志消息
        }
    """
    scores = compute_frequency_scores(days=days)
    ws_ids = _get_workspace_ids()

    if not ws_ids:
        return {"changed": False, "new_order": [], "scores": {}, "message": "无工作区"}

    # 读取每个工作区的当前状态
    ws_data: dict[str, dict] = {}
    for wid in ws_ids:
        data = _read_workspace_json(wid)
        if data is not None:
            ws_data[wid] = data

    # 分别处理：已手动排序的 vs 未手动排序的
    manual_ids = {wid for wid, d in ws_data.items() if d.get("manual_sort")}
    auto_ids = [wid for wid in ws_data if wid not in manual_ids]

    # 未手动排序的：按使用频率降序排列
    def sort_key(wid):
        s = scores.get(wid, 0)
        orig = ws_data[wid].get("sort_order", 99)
        return (-s if s > 0 else 1, orig)

    auto_ids.sort(key=sort_key)

    # 已手动排序的：保持当前 sort_order 不变（不重新分配位置）
    manual_ordered = sorted(
        manual_ids,
        key=lambda wid: ws_data[wid].get("sort_order", 99),
    )
    new_order = auto_ids + manual_ordered

    # 写入新的 sort_order（跳过 manual_sort 标记的工作区）
    updated = []
    for i, wid in enumerate(new_order):
        d = ws_data.get(wid)
        if d is not None:
            if d.get("manual_sort"):
                continue  # 手动排序的保持原位，不修改
            d["sort_order"] = i
            if _write_workspace_json(wid, d):
                updated.append(wid)

    # 重新发现以刷新内存
    try:
        from .workspace_manager import manager
        manager.discover()
    except ImportError:
        pass

    # 构建日志消息
    score_lines = []
    for wid in new_order:
        s = scores.get(wid, 0)
        flag = " [手动]" if wid in manual_ids else ""
        score_lines.append(f"  {wid}: {s} 分{flag}")
    score_str = "\n".join(score_lines)

    msg = (
        f"已根据近 {days} 天使用习惯优化工作区顺序\n"
        f"--- 排序详情 ---\n{score_str}"
    )

    return {
        "changed": True,
        "new_order": new_order,
        "scores": scores,
        "message": msg,
        "updated": updated,
    }
