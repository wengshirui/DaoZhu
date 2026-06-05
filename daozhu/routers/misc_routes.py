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


# === 窗口 focus 事件（#073 优化点4）===
@router.post("/api/focus")
async def on_focus():
    """窗口获得焦点时调用，触发智能检查"""
    from daozhu.idle_worker import on_window_focus, record_interaction
    record_interaction("focus")
    await on_window_focus()
    return {"ok": True}


# === 管家问候 API（#073 Phase 1）===
@router.get("/api/greeting")
async def get_greeting(conversation_id: str = None):
    """
    管家主动开口。三种场景：
    1. 未配置 API key → 固定引导语
    2. 新对话（无 conversation_id）→ 时间 + 待办数据（零 token）
    3. 有历史对话（传 conversation_id）→ 调 LLM 总结 + 待办（少量 token）

    思想基石：用户是谁 → 他想干什么 → 怎么帮他更好地实现
    """
    import httpx
    from datetime import datetime, date
    from daozhu.config import get_config_value, get_api_key

    # 检查开关
    enabled = get_config_value("greeting.enabled", True)
    if not enabled:
        return {"greeting": "", "has_todo_data": False, "source": "disabled"}

    # 检查 API key 是否配置
    api_key = get_api_key()
    has_key = bool(api_key)

    # 场景 1：未配置 key
    if not has_key:
        return {
            "greeting": "你好，我是岛管理员。告诉我你想建造什么工作区，或者问我任何问题。\n\n⚠️ 但你需要先在设置里配置 LLM 的 API Key，我才能正常工作。",
            "has_todo_data": False,
            "source": "no_key",
        }

    # 场景 0.5：未完成 onboarding（AI 对用户还一无所知）
    from daozhu.memory_db import get_profile, get_all_profiles
    all_profiles = get_all_profiles()
    # 如果 profile 条目 >= 3，说明已通过对话了解了用户，跳过 onboarding
    if len(all_profiles) < 3:
        return {
            "greeting": "你好！我是你的 AI 伙伴。为了更好地帮到你，能简单告诉我：\n\n1️⃣ 你的岗位是什么？（如产品经理、开发、设计师…）\n2️⃣ 你日常工作中最烦的重复事务是什么？\n\n这样我就知道怎么主动帮你了。",
            "has_todo_data": False,
            "source": "onboarding",
        }

    # 场景 0.8：有未展示的 AI 自主工作汇报（AC8）
    from daozhu.idle_worker import get_pending_report
    report = get_pending_report()
    if report:
        return {
            "greeting": f"你不在的时候我做了些事：\n\n{report['summary']}",
            "has_todo_data": True,
            "source": "idle_report",
            "report": report,
        }

    # 时间问候
    now = datetime.now()
    hour = now.hour
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
    name = get_profile("称呼") or get_profile("nickname") or ""
    if name:
        time_greeting = f"{time_greeting}，{name}"

    # 获取待办数据（降级处理）
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
        todo_summary = ""

    # 场景 3：有历史对话 → 调 LLM 做个性化问候
    if conversation_id:
        try:
            from daozhu.chat_db import get_conversation
            conv = get_conversation(conversation_id)
            if conv and conv.get("messages"):
                # 取最近 5 条消息做上下文
                recent = conv["messages"][-5:]
                context_lines = []
                for msg in recent:
                    role = "用户" if msg["role"] == "user" else "管家"
                    content = (msg.get("content") or "")[:100]
                    if content:
                        context_lines.append(f"{role}: {content}")

                if context_lines:
                    context_str = "\n".join(context_lines)

                    # 构建用户画像上下文
                    profile_str = ""
                    if all_profiles:
                        # 取最相关的 profile 条目（身份/工作相关优先）
                        priority_keys = {"岗位", "职位", "职业", "身份", "角色", "称呼",
                                        "关注领域", "迭代节奏", "管理项目", "活跃时段", "主要用途"}
                        key_profiles = [p for p in all_profiles if p["key"] in priority_keys]
                        if not key_profiles:
                            key_profiles = all_profiles[:5]  # fallback: 取前5条
                        if key_profiles:
                            profile_str = "用户画像：" + "、".join(
                                f"{p['key']}={p['value']}" for p in key_profiles[:6])

                    # 调 LLM 生成简短问候
                    from daozhu.chat_service import call_llm_simple
                    prompt = f"""你是用户的 AI 伙伴（不是仆人，是平等的朋友和搭档）。用户回来了，请用一句话主动问候。
要求：简短（不超过40字）、自然、平等语气。结合上下文提醒重要事项。
禁止：不要用"主人"、"您"等敬语，用"你"就好。不要过度热情或谄媚。

{profile_str}

最近对话：
{context_str}

{"待办情况：" + todo_summary if todo_summary else ""}

请直接输出问候语（不要解释）："""
                    llm_greeting = await call_llm_simple(prompt, max_tokens=80)
                    if llm_greeting:
                        return {
                            "greeting": llm_greeting.strip(),
                            "has_todo_data": bool(todo_summary),
                            "source": "llm",
                        }
        except Exception:
            pass  # LLM 失败时 fallback 到模板

    # 场景 2：新对话 / LLM fallback → 纯模板
    parts = [time_greeting + "。"]
    if todo_summary:
        parts.append(todo_summary)
    if not todo_summary:
        parts.append("有什么我能帮你的？")

    return {
        "greeting": "".join(parts),
        "has_todo_data": bool(todo_summary),
        "source": "template",
    }
