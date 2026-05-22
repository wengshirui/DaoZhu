"""AccoBot Web Server — FastAPI backend with WebSocket chat.

Usage:
    python -m accobot.web.server
    # or: accobot web

Routes are split into modular files under accobot/web/routes/:
    config.py  — Config, companies, gateway, user profile
    files.py   — File upload, attachments
    chat.py    — Chat history sessions
    ledger.py  — Accounts, vouchers, ledger, tax, overview, todos
    mcp.py     — MCP servers, skills, browser check
"""

import asyncio
import json
import logging
import webbrowser
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from accobot import __version__
from accobot.config import ensure_home, load_config, load_env
from accobot.agent import AccoAgent
from accobot.tools.registry import registry, discover_tools
from accobot.web.routes import register_routes

logger = logging.getLogger(__name__)

app = FastAPI(title="AccoBot", version=__version__)

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Register all API routes
register_routes(app)


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main chat page."""
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


# =========================================================================
# WebSocket Chat
# =========================================================================

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat."""
    await websocket.accept()

    load_env()
    config = load_config()

    try:
        agent = AccoAgent(config=config)
    except ValueError as e:
        await websocket.send_json({"type": "error", "content": str(e)})
        await websocket.close()
        return

    stop_requested = {"value": False}

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "stop":
                stop_requested["value"] = True
                await websocket.send_json({"type": "done"})
                continue

            user_message = msg.get("message", "")
            if not user_message:
                continue

            stop_requested["value"] = False
            await _run_agent_turn(websocket, agent, user_message, stop_requested)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception("WebSocket error: %s", e)
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass


async def _run_agent_turn(websocket: WebSocket, agent: AccoAgent, user_message: str, stop_requested: dict = None):
    """Execute one agent turn with streaming updates to the client."""
    if stop_requested is None:
        stop_requested = {"value": False}

    agent.messages.append({"role": "user", "content": user_message})

    iteration = 0
    while iteration < agent.max_iterations:
        iteration += 1

        if stop_requested["value"]:
            agent.messages.append({"role": "assistant", "content": "（已被用户中断）"})
            await websocket.send_json({"type": "done"})
            return

        tool_defs = registry.get_definitions()

        kwargs = {
            "model": agent.model,
            "messages": agent.messages,
        }
        if tool_defs:
            kwargs["tools"] = tool_defs
            kwargs["tool_choice"] = "auto"

        try:
            stream = agent.client.chat.completions.create(stream=True, **kwargs)

            content_parts = []
            tool_calls_data = {}

            for chunk in stream:
                delta = chunk.choices[0].delta

                if delta.content:
                    content_parts.append(delta.content)
                    await websocket.send_json({
                        "type": "token",
                        "content": delta.content,
                    })

                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_calls_data:
                            tool_calls_data[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc_delta.id:
                            tool_calls_data[idx]["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tool_calls_data[idx]["name"] = tc_delta.function.name
                            if tc_delta.function.arguments:
                                tool_calls_data[idx]["arguments"] += tc_delta.function.arguments

            if tool_calls_data:
                assistant_msg = {
                    "role": "assistant",
                    "content": "".join(content_parts) or "",
                    "tool_calls": [
                        {
                            "id": tool_calls_data[idx]["id"],
                            "type": "function",
                            "function": {
                                "name": tool_calls_data[idx]["name"],
                                "arguments": tool_calls_data[idx]["arguments"],
                            },
                        }
                        for idx in sorted(tool_calls_data.keys())
                    ],
                }
                agent.messages.append(assistant_msg)

                for idx in sorted(tool_calls_data.keys()):
                    tc = tool_calls_data[idx]
                    name = tc["name"]
                    try:
                        args = json.loads(tc["arguments"])
                    except json.JSONDecodeError:
                        args = {}

                    await websocket.send_json({
                        "type": "tool_call",
                        "name": name,
                        "args": args,
                    })

                    result = registry.dispatch(name, args)

                    await websocket.send_json({
                        "type": "tool_result",
                        "name": name,
                        "result": result,
                    })

                    agent.messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })
            else:
                content = "".join(content_parts)
                agent.messages.append({"role": "assistant", "content": content})
                await websocket.send_json({"type": "done"})
                return

        except Exception as e:
            logger.exception("Agent turn error: %s", e)
            error_msg = f"调用模型时出错：{e}"
            agent.messages.append({"role": "assistant", "content": error_msg})
            await websocket.send_json({"type": "error", "content": error_msg})
            return

    await websocket.send_json({
        "type": "error",
        "content": "操作步骤较多，已达到单次对话的处理上限。",
    })


# =========================================================================
# Server Entry Point
# =========================================================================

def start_server(host: str = "127.0.0.1", port: int = 9120, open_browser: bool = True):
    """Start the web server."""
    import uvicorn

    ensure_home()
    load_env()
    discover_tools()

    try:
        from accobot.proactive import start_proactive
        start_proactive()
    except Exception as e:
        logger.debug("Proactive engine start failed: %s", e)

    if open_browser:
        import threading
        def _open():
            import time
            time.sleep(1.5)
            webbrowser.open(f"http://{host}:{port}")
        threading.Thread(target=_open, daemon=True).start()

    print(f"\n  AccoBot Web UI: http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_server()
