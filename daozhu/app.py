"""
岛主 DaoZhu — 平台主服务
端口: 7788
职责: 托管书架 UI + 提供 API + 管理工作区生命周期
"""

from contextlib import asynccontextmanager
from pathlib import Path
import json

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import load_config, get_config_value, set_config_value
from .workspace_manager import manager
from .chat_db import (
    init_chat_db, create_conversation, list_conversations,
    get_conversation, delete_conversation, add_message,
    update_conversation_title,
)
from .chat_service import chat_stream
from .memory_db import init_memory_db, get_skill_stats, get_stale_skills
from .memory_service import build_memory_context, extract_memories
from .agent import agent_chat_stream

# 静态文件目录
FRONTEND_DIR = Path(__file__).parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """平台生命周期：启动时发现工作区，关闭时清理"""
    init_chat_db()
    init_memory_db()
    await manager.startup()
    yield
    await manager.shutdown()


app = FastAPI(title="岛主 DaoZhu", version="0.1.0", lifespan=lifespan)


# === 页面路由 ===
@app.get("/")
async def index():
    """返回主界面"""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/favicon.svg")
async def favicon():
    """返回 favicon"""
    return FileResponse(FRONTEND_DIR / "favicon.svg", media_type="image/svg+xml")


@app.get("/onboarding")
async def onboarding_page():
    """引导页面"""
    return FileResponse(FRONTEND_DIR / "onboarding.html")


@app.post("/api/onboarding/save-key")
async def save_api_key(body: dict):
    """保存 API Key 到 .env 文件"""
    key = body.get("key", "").strip()
    if not key:
        raise HTTPException(400, "Key 不能为空")

    from .config import PLATFORM_ROOT
    env_path = PLATFORM_ROOT / ".env"
    # 读取现有内容
    existing = ""
    if env_path.exists():
        existing = env_path.read_text(encoding="utf-8")

    # 替换或追加
    lines = existing.split("\n")
    found = False
    for i, line in enumerate(lines):
        if line.startswith("DEEPSEEK_API_KEY="):
            lines[i] = f"DEEPSEEK_API_KEY={key}"
            found = True
            break
    if not found:
        lines.append(f"DEEPSEEK_API_KEY={key}")

    env_path.write_text("\n".join(lines), encoding="utf-8")
    return {"success": True}


# === 静态资源 ===
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")


# === 工作区 API ===
@app.get("/api/workspaces")
async def get_workspaces():
    """获取工作区列表"""
    workspaces = manager.list_workspaces()
    return {"workspaces": workspaces}


@app.post("/api/workspaces/{workspace_id}/start")
async def start_workspace(workspace_id: str):
    """启动工作区"""
    try:
        ws = await manager.start_workspace(workspace_id)
        return {"success": True, "workspace": ws.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspaces/{workspace_id}/stop")
async def stop_workspace(workspace_id: str):
    """停止工作区"""
    try:
        ws = await manager.stop_workspace(workspace_id)
        return {"success": True, "workspace": ws.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/workspaces/{workspace_id}/hide")
async def hide_workspace(workspace_id: str):
    """隐藏工作区"""
    try:
        manager.hide_workspace(workspace_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/workspaces/{workspace_id}/unhide")
async def unhide_workspace(workspace_id: str):
    """取消隐藏工作区"""
    try:
        manager.unhide_workspace(workspace_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/workspaces/refresh")
async def refresh_workspaces():
    """重新扫描工作区目录"""
    manager.discover()
    return {"success": True, "count": len(manager.workspaces)}


# === 技能 API ===
@app.get("/api/skills")
async def get_skills():
    """获取技能列表（从 skills/ 目录扫描）"""
    from .skill_loader import discover_skills
    skills = discover_skills()
    # 转为前端期望的格式
    result = [
        {"id": s["id"], "name": s["name"], "icon": "📖", "status": "active"}
        for s in skills
    ]
    return {"skills": result}


# === 工具 API ===
@app.get("/api/tools")
async def get_tools():
    """获取已注册工具列表"""
    from .tools.registry import registry
    tools = registry.list_tools()
    # 转为前端期望的格式
    result = [
        {"id": t["name"], "name": t["description"][:20], "icon": t["emoji"], "status": "connected"}
        for t in tools
    ]
    return {"tools": result}


# === 对话 API ===
@app.get("/api/conversations")
async def get_conversations_api():
    """获取历史对话列表"""
    conversations = list_conversations()
    return {"conversations": conversations}


@app.get("/api/conversations/{conv_id}")
async def get_conversation_api(conv_id: str):
    """获取单个会话详情"""
    conv = get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conv


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation_api(conv_id: str):
    """删除会话"""
    if not delete_conversation(conv_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True}


@app.post("/api/chat")
async def chat_api(body: dict):
    """发送消息并获取 AI 流式响应（SSE）"""
    from starlette.responses import StreamingResponse

    message = body.get("message", "").strip()
    conv_id = body.get("conversation_id")

    if not message:
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 创建或获取会话
    if not conv_id:
        conv = create_conversation(title=message[:20])
        conv_id = conv["id"]

    # 保存用户消息
    add_message(conv_id, "user", message)

    # 获取会话历史作为上下文
    conv_data = get_conversation(conv_id)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in conv_data["messages"]
    ]

    # 流式响应
    async def generate():
        full_response = ""

        # 构建记忆上下文
        memory_context = build_memory_context(message)

        async for chunk in agent_chat_stream(history, memory_context=memory_context):
            # 工具调用通知（特殊标记）
            if chunk.startswith("[TOOL:"):
                tool_name = chunk[6:-1]
                yield f"data: {json.dumps({'tool': tool_name, 'conversation_id': conv_id})}\n\n"
                continue

            full_response += chunk
            yield f"data: {json.dumps({'chunk': chunk, 'conversation_id': conv_id})}\n\n"

        # 保存完整的 AI 回复
        add_message(conv_id, "assistant", full_response)

        # 如果是第一条消息，用内容更新标题
        if len(history) <= 1:
            title = message[:30] + ("..." if len(message) > 30 else "")
            update_conversation_title(conv_id, title)

        # 异步提取记忆（不阻塞响应）
        import asyncio
        all_messages = history + [{"role": "assistant", "content": full_response}]
        asyncio.create_task(extract_memories(all_messages, conv_id))

        yield f"data: {json.dumps({'done': True, 'conversation_id': conv_id})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# === 配置 API ===
@app.get("/api/config")
async def get_config():
    """获取平台配置"""
    config = load_config()
    return {"config": config}


@app.put("/api/config/{path:path}")
async def update_config(path: str, body: dict):
    """更新配置项"""
    value = body.get("value")
    if value is None:
        raise HTTPException(status_code=400, detail="缺少 value 字段")
    set_config_value(path, value)
    return {"success": True, "path": path, "value": value}


# === 记忆 API ===
@app.get("/api/memory/profile")
async def get_memory_profile():
    """获取用户画像"""
    from .memory_db import get_all_profiles
    return {"profiles": get_all_profiles()}


@app.get("/api/memory/knowledge")
async def get_memory_knowledge(q: str = ""):
    """搜索/获取知识库"""
    from .memory_db import search_knowledge, get_recent_knowledge
    if q:
        return {"knowledge": search_knowledge(q)}
    return {"knowledge": get_recent_knowledge()}


@app.get("/api/memory/skills")
async def get_skill_stats_api():
    """获取 skill 使用统计"""
    return {"stats": get_skill_stats(), "stale": get_stale_skills()}


if __name__ == "__main__":
    import uvicorn
    port = get_config_value("platform.port", 7788)
    uvicorn.run(app, host="0.0.0.0", port=port)
