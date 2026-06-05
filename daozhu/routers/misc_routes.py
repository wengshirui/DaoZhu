import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from ..config import load_config, set_config_value

router = APIRouter()

# === 技能 API ===
@router.get("/api/skills")
async def get_skills():
    """获取技能列表（从 skills/ 目录扫描）"""
    from daozhu.skill_loader import discover_skills
    skills = discover_skills()
    result = [
        {"id": s["id"], "name": s["name"], "icon": "📖", "status": "active"}
        for s in skills
    ]
    return {"skills": result}


@router.get("/api/skills/{skill_id}/readme")
async def get_skill_readme(skill_id: str):
    """获取技能的 SKILL.md 内容"""
    from daozhu.skill_loader import load_skill
    content = load_skill(skill_id)
    if not content:
        raise HTTPException(404, "技能不存在")
    return {"id": skill_id, "content": content}


@router.delete("/api/skills/{skill_id}")
async def delete_skill(skill_id: str):
    """删除技能（删除 SKILL.md 文件）"""
    from daozhu.config import PLATFORM_ROOT
    skill_dir = PLATFORM_ROOT / "skills" / skill_id
    if not skill_dir.exists():
        raise HTTPException(404, "技能不存在")
    import shutil
    shutil.rmtree(str(skill_dir))
    return {"success": True}


# === 工具 API ===
@router.get("/api/tools")
async def get_tools():
    """获取已注册工具列表"""
    from daozhu.tools.registry import registry
    tools = registry.list_tools()
    result = [
        {"id": t["name"], "name": t["description"][:20], "icon": t["emoji"],
         "status": "connected",
         "description": t["description"]}
        for t in tools
    ]
    return {"tools": result}



# === 版本 API ===
@router.get("/api/version")
async def get_version():
    """获取项目版本号和 Git 信息"""
    import subprocess
    from daozhu.config import PLATFORM_ROOT

    # 从 pyproject.toml 读取版本
    version = "unknown"
    toml_path = PLATFORM_ROOT / "pyproject.toml"
    if toml_path.exists():
        for line in toml_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("version"):
                version = line.split('"')[1]
                break

    # 尝试获取 Git 信息
    git_hash = None
    git_time = None
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%h|%ci"],
            cwd=PLATFORM_ROOT, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split("|", 1)
            git_hash = parts[0]
            git_time = parts[1] if len(parts) > 1 else None
    except Exception:
        pass

    return {
        "version": version,
        "git_hash": git_hash,
        "git_time": git_time,
    }


# === 配置 API ===
@router.get("/api/config")
async def get_config():
    """获取平台配置"""
    config = load_config()
    return {"config": config}


@router.put("/api/config/{path:path}")
async def update_config(path: str, body: dict):
    """更新配置项"""
    value = body.get("value")
    if value is None:
        raise HTTPException(status_code=400, detail="缺少 value 字段")
    set_config_value(path, value)
    return {"success": True, "path": path, "value": value}


# === 记忆 API ===
@router.get("/api/memory/profile")
async def get_memory_profile():
    """获取用户画像"""
    from daozhu.memory_db import get_all_profiles
    return {"profiles": get_all_profiles()}


@router.get("/api/config/secrets-status")
async def get_secrets_status():
    """获取密钥配置状态（不返回值，只返回是否已配置）"""
    from daozhu.config_db import get_secret
    return {
        "deepseek": bool(get_secret("DEEPSEEK_API_KEY")),
        "zhipu": bool(get_secret("ZHIPU_API_KEY")),
        "openai": bool(get_secret("OPENAI_API_KEY")),
        "gitee": bool(get_secret("GITEE_TOKEN")),
    }


@router.get("/api/memory/knowledge")
async def get_memory_knowledge(q: str = ""):
    """搜索/获取知识库"""
    from daozhu.memory_db import search_knowledge, get_recent_knowledge
    if q:
        return {"knowledge": search_knowledge(q)}
    return {"knowledge": get_recent_knowledge()}


@router.get("/api/memory/skills")
async def get_skill_stats_api():
    """获取工具使用统计"""
    from daozhu.tool_log_db import get_tool_stats, get_stale_tools
    return {"stats": get_tool_stats(), "stale": get_stale_tools()}


# === 宠物 API（供主界面浮动宠物使用） ===
@router.get("/api/pet/active")
async def get_active_pet():
    """获取当前活跃宠物的 spritesheet 信息（供主界面浮动宠物渲染）"""
    from daozhu.config import PLATFORM_ROOT
    import sqlite3

    pet_db = PLATFORM_ROOT / "workspaces" / "desktop-pet" / "data.db"
    if not pet_db.exists():
        return {"pet": None}

    try:
        conn = sqlite3.connect(str(pet_db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, name, display_name, local_path FROM pets WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        conn.close()

        if not row:
            return {"pet": None}

        # 构建 spritesheet URL（通过工作区静态文件服务）
        name = row["name"]
        return {
            "pet": {
                "id": row["id"],
                "name": name,
                "displayName": row["display_name"] or name,
                "spritesheetUrl": f"/pets/{name}/spritesheet.webp",
            }
        }
    except Exception:
        return {"pet": None}


# === Agent 成长 API（#069）===
@router.post("/api/growth/run")
async def api_growth_run():
    """手动触发成长"""
    from daozhu.growth import run_growth
    result = run_growth()
    return {"success": True, **result}


@router.get("/api/growth/reports")
async def api_growth_reports():
    """获取成长报告"""
    from daozhu.growth import get_growth_reports
    return {"reports": get_growth_reports()}


# === 定时任务 API（#067）===
@router.get("/api/scheduler/tasks")
async def list_scheduled_tasks():
    """列出所有定时任务"""
    from daozhu.scheduler import list_tasks
    return {"tasks": list_tasks()}


@router.post("/api/scheduler/tasks")
async def create_scheduled_task(body: dict):
    """创建定时任务"""
    from daozhu.scheduler import create_task
    name = body.get("name", "").strip()
    task_type = body.get("task_type", "ai_prompt")
    payload = body.get("payload", "").strip()
    schedule = body.get("schedule", "24h")
    description = body.get("description", "")

    if not name or not payload:
        raise HTTPException(400, "name 和 payload 不能为空")

    task = create_task(name, task_type, payload, schedule, description)
    return {"success": True, "task": task}


@router.put("/api/scheduler/tasks/{task_id}")
async def update_scheduled_task(task_id: int, body: dict):
    """更新定时任务"""
    from daozhu.scheduler import update_task
    task = update_task(task_id, **body)
    if not task:
        raise HTTPException(404, "任务不存在")
    return {"success": True, "task": task}


@router.delete("/api/scheduler/tasks/{task_id}")
async def delete_scheduled_task(task_id: int):
    """删除定时任务"""
    from daozhu.scheduler import delete_task
    if not delete_task(task_id):
        raise HTTPException(404, "任务不存在")
    return {"success": True}


@router.get("/api/scheduler/tasks/{task_id}/runs")
async def get_task_run_history(task_id: int):
    """获取任务执行历史"""
    from daozhu.scheduler import get_task_runs
    return {"runs": get_task_runs(task_id)}


# === 管家问候 API（#073 Phase 1）===
@router.get("/api/greeting")
async def get_greeting():
    """
    管家主动开口：基于时间 + 待办数据生成问候语。
    不消耗 LLM token，纯逻辑拼接。
    思想基石：用户是谁 → 他想干什么 → 怎么帮他更好地实现
    """
    import httpx
    from datetime import datetime, date

    now = datetime.now()
    hour = now.hour

    # 时间段问候
    if 5 <= hour < 9:
        time_greeting = "早上好"
    elif 9 <= hour < 12:
        time_greeting = "上午好"
    elif 12 <= hour < 14:
        time_greeting = "中午好"
    elif 14 <= hour < 18:
        time_greeting = "下午好"
    elif 18 <= hour < 22:
        time_greeting = "晚上好"
    else:
        time_greeting = "夜深了，注意休息"

    # 尝试获取用户称呼
    from daozhu.memory_db import get_profile
    name = get_profile("称呼") or get_profile("nickname") or ""
    if name:
        time_greeting = f"{time_greeting}，{name}"

    # 尝试获取待办数据（降级处理）
    todo_summary = ""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://localhost:7801/api/tasks/", params={"today": "true"})
            if resp.status_code == 200:
                data = resp.json()
                tasks = data.get("tasks", [])
                active = [t for t in tasks if t.get("status") != "done"]
                overdue = [t for t in active if t.get("due_date") and t["due_date"] <= date.today().isoformat()]
                high_priority = [t for t in active if t.get("priority") == "high"]

                if overdue:
                    todo_summary = f"你有 {len(overdue)} 个待办已到期，需要优先处理。"
                elif high_priority:
                    todo_summary = f"今天有 {len(high_priority)} 个高优先级待办。"
                elif active:
                    todo_summary = f"今天有 {len(active)} 个待办事项。"
                else:
                    todo_summary = "今天的待办都完成了，做得不错。"
    except Exception:
        # 待办服务不可用，优雅降级
        todo_summary = ""

    # 拼接问候语
    parts = [time_greeting + "。"]
    if todo_summary:
        parts.append(todo_summary)
    if not todo_summary:
        parts.append("有什么我能帮你的？")

    greeting = "".join(parts)

    return {"greeting": greeting, "has_todo_data": bool(todo_summary)}
