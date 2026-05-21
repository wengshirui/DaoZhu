"""AccoBot Web Server — FastAPI backend with WebSocket chat.

Usage:
    python -m accobot.web.server
    # or: accobot web
"""

import asyncio
import json
import logging
import os
import uuid
import webbrowser
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from accobot import __version__
from accobot.config import ensure_home, load_config, load_env, get_api_key
from accobot.agent import AccoAgent
from accobot.tools.registry import registry, discover_tools

logger = logging.getLogger(__name__)

app = FastAPI(title="AccoBot", version=__version__)

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main chat page."""
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.get("/api/status")
async def status():
    """Return system status."""
    discover_tools()
    load_env()
    has_api_key = bool(get_api_key())
    return {
        "version": __version__,
        "tools": registry.get_all_tool_names(),
        "tool_count": len(registry.get_all_tool_names()),
        "has_api_key": has_api_key,
    }


@app.get("/api/config")
async def get_config_api():
    """Return current config (redacted)."""
    load_env()
    config = load_config()
    has_key = bool(get_api_key())
    return {
        "model": config.get("model", {}),
        "user": config.get("user", {}),
        "has_api_key": has_key,
    }


@app.post("/api/config/apikey")
async def save_api_key(request: dict):
    """Save API key to .env file."""
    from accobot.config import get_env_path, ensure_home
    key = request.get("api_key", "").strip()
    provider = request.get("provider", "deepseek").strip()

    if not key:
        return {"success": False, "error": "API Key 不能为空"}

    ensure_home()
    env_path = get_env_path()

    # Read existing .env content
    existing = ""
    if env_path.exists():
        existing = env_path.read_text(encoding="utf-8")

    # Determine env var name
    env_var = "DEEPSEEK_API_KEY" if provider == "deepseek" else "OPENAI_API_KEY"

    # Replace or append
    lines = existing.splitlines() if existing else []
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{env_var}="):
            lines[i] = f"{env_var}={key}"
            found = True
            break
    if not found:
        lines.append(f"{env_var}={key}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Reload env
    os.environ[env_var] = key
    load_env()

    return {"success": True, "message": "API Key 已保存"}


@app.post("/api/config/model")
async def save_model_config(request: dict):
    """Save model configuration."""
    from accobot.config import save_config
    config = load_config()

    if "provider" in request:
        config["model"]["provider"] = request["provider"]
    if "model_name" in request:
        config["model"]["model_name"] = request["model_name"]
    if "base_url" in request:
        config["model"]["base_url"] = request["base_url"]

    save_config(config)
    return {"success": True, "message": "模型配置已保存"}


@app.get("/api/companies")
async def get_companies():
    """Return list of companies (account sets) and current selection."""
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    companies = mgr.master.list_companies()
    current = mgr.current_company_id
    return {
        "companies": [{"id": c["id"], "name": c["name"], "industry": c.get("industry", "")} for c in companies],
        "current": current,
    }


@app.post("/api/companies/switch")
async def switch_company(request: dict):
    """Switch active company (account set)."""
    from accobot.db.manager import DBManager
    company_id = request.get("company_id")
    if not company_id:
        return {"success": False, "error": "未指定账套"}
    mgr = DBManager.get_instance()
    ok = mgr.switch_company(company_id)
    if not ok:
        return {"success": False, "error": "账套不存在"}
    return {"success": True, "company_id": company_id}


@app.post("/api/companies/create")
async def create_company(request: dict):
    """Create a new company (account set)."""
    from accobot.db.manager import DBManager
    name = request.get("name", "").strip()
    if not name:
        return {"success": False, "error": "公司名称不能为空"}
    mgr = DBManager.get_instance()
    result = mgr.create_company(
        name=name,
        industry=request.get("industry", ""),
        taxpayer_type=request.get("taxpayer_type", "small_scale"),
        accounting_standard=request.get("accounting_standard", "small_enterprise"),
    )
    return {"success": True, "company": result}


@app.post("/api/companies/open-folder")
async def open_company_folder(request: dict):
    """Open the company data folder in system file manager."""
    import subprocess
    import sys
    from accobot.db.manager import DBManager

    company_id = request.get("company_id")
    mgr = DBManager.get_instance()
    company_dir = mgr.get_company_dir(company_id)

    if not company_dir or not company_dir.exists():
        return {"success": False, "error": "账套文件夹不存在"}

    # Open folder with system file manager
    try:
        if sys.platform == "win32":
            os.startfile(str(company_dir))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(company_dir)])
        else:
            subprocess.Popen(["xdg-open", str(company_dir)])
        return {"success": True, "path": str(company_dir)}
    except Exception as e:
        return {"success": False, "error": f"无法打开文件夹：{e}"}


@app.post("/api/companies/delete")
async def delete_company_api(request: dict):
    """Delete a company (requires confirm_name matching company name)."""
    from accobot.db.manager import DBManager
    company_id = request.get("company_id", "")
    confirm_name = request.get("confirm_name", "")

    if not company_id:
        return {"success": False, "error": "未指定账套"}
    if not confirm_name:
        return {"success": False, "error": "请输入公司名称确认删除"}

    mgr = DBManager.get_instance()
    result = mgr.delete_company(company_id, confirm_name)
    return result


# =========================================================================
# File Upload API
# =========================================================================

from fastapi import UploadFile


@app.post("/api/upload/file")
async def handle_file_upload(file: UploadFile):
    """Upload a single file. Stores in the current company's documents folder."""
    from accobot.db.manager import DBManager
    from datetime import date as date_mod

    mgr = DBManager.get_instance()
    if not mgr.current_company_id:
        return {"success": False, "error": "请先选择账套"}

    company_dir = mgr.get_company_dir(mgr.current_company_id)
    if not company_dir:
        return {"success": False, "error": "账套文件夹不存在"}

    # Determine target folder (documents/YYYY-MM/)
    today = date_mod.today()
    period_folder = f"{today.year}-{today.month:02d}"
    target_dir = company_dir / "documents" / period_folder
    target_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    filename = file.filename or f"upload_{today.isoformat()}_{uuid.uuid4().hex[:6]}"
    # Sanitize filename
    safe_name = "".join(c for c in filename if c.isalnum() or c in ".-_ ()（）")
    if not safe_name:
        safe_name = f"file_{uuid.uuid4().hex[:8]}"

    target_path = target_dir / safe_name
    # Avoid overwrite
    if target_path.exists():
        stem = target_path.stem
        suffix = target_path.suffix
        target_path = target_dir / f"{stem}_{uuid.uuid4().hex[:4]}{suffix}"

    content = await file.read()
    target_path.write_bytes(content)

    return {
        "success": True,
        "filename": target_path.name,
        "path": str(target_path),
        "size": len(content),
        "period": period_folder,
        "message": f"文件 {target_path.name} 已上传到 {period_folder}/",
    }


@app.get("/api/files/list")
async def list_uploaded_files(period: str = None):
    """List uploaded files for the current company."""
    from accobot.db.manager import DBManager

    mgr = DBManager.get_instance()
    if not mgr.current_company_id:
        return {"files": [], "error": "请先选择账套"}

    company_dir = mgr.get_company_dir(mgr.current_company_id)
    if not company_dir:
        return {"files": [], "error": "账套文件夹不存在"}

    docs_dir = company_dir / "documents"
    if not docs_dir.exists():
        return {"files": [], "periods": []}

    files = []
    periods = []

    for period_dir in sorted(docs_dir.iterdir()):
        if not period_dir.is_dir():
            continue
        periods.append(period_dir.name)
        if period and period_dir.name != period:
            continue
        for f in sorted(period_dir.iterdir()):
            if f.is_file():
                files.append({
                    "name": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "period": period_dir.name,
                })

    return {"files": files, "periods": periods, "count": len(files)}


@app.post("/api/attachments/link")
async def link_attachment(request: dict):
    """Link an uploaded file to a voucher."""
    from accobot.db.manager import DBManager

    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"success": False, "error": "请先选择账套"}

    voucher_id = request.get("voucher_id", "")
    file_path = request.get("file_path", "")
    filename = request.get("filename", "")

    if not voucher_id or not file_path:
        return {"success": False, "error": "缺少凭证ID或文件路径"}

    # Verify voucher exists
    voucher = mgr.accounting.get_voucher_with_entries(voucher_id)
    if not voucher:
        return {"success": False, "error": f"凭证 {voucher_id} 不存在"}

    from pathlib import Path as P
    fp = P(file_path)
    size = fp.stat().st_size if fp.exists() else 0
    name = filename or fp.name

    att_id = mgr.accounting.add_attachment(voucher_id, name, file_path, file_size=size)
    return {"success": True, "attachment_id": att_id, "message": f"附件 {name} 已关联到凭证 {voucher_id}"}


@app.get("/api/attachments/{voucher_id}")
async def get_attachments(voucher_id: str):
    """Get attachments for a voucher."""
    from accobot.db.manager import DBManager

    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"attachments": [], "error": "请先选择账套"}

    attachments = mgr.accounting.get_attachments(voucher_id)
    return {"attachments": attachments, "count": len(attachments)}


# =========================================================================
# Chat History API
# =========================================================================

def _get_chat_db():
    """Get or create the chat history DB singleton."""
    if not hasattr(_get_chat_db, "_instance"):
        from accobot.db.chat_history import ChatHistoryDB
        _get_chat_db._instance = ChatHistoryDB()
    return _get_chat_db._instance


@app.get("/api/chat/sessions")
async def list_chat_sessions():
    """List recent chat sessions."""
    db = _get_chat_db()
    sessions = db.list_sessions()
    return {"sessions": sessions}


@app.post("/api/chat/sessions")
async def create_chat_session(request: dict = None):
    """Create a new chat session."""
    db = _get_chat_db()
    title = (request or {}).get("title", "新对话")
    session = db.create_session(title=title)
    return {"success": True, "session": session}


@app.get("/api/chat/sessions/{session_id}/messages")
async def get_chat_messages(session_id: str):
    """Get messages for a chat session."""
    db = _get_chat_db()
    messages = db.get_messages(session_id)
    return {"messages": messages}


@app.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session."""
    db = _get_chat_db()
    db.delete_session(session_id)
    return {"success": True}


@app.post("/api/chat/sessions/{session_id}/messages")
async def add_chat_message(session_id: str, request: dict):
    """Add a message to a chat session."""
    db = _get_chat_db()
    role = request.get("role", "user")
    content = request.get("content", "")
    msg_id = db.add_message(session_id, role, content)
    return {"success": True, "message_id": msg_id}


@app.patch("/api/chat/sessions/{session_id}")
async def update_chat_session(session_id: str, request: dict):
    """Update a chat session (e.g., title)."""
    db = _get_chat_db()
    title = request.get("title")
    if title:
        db.update_session_title(session_id, title)
    return {"success": True}


# =========================================================================
# Data Overview API
# =========================================================================

@app.get("/api/data/overview")
async def data_overview():
    """Return key financial metrics for the left panel data display."""
    from accobot.db.manager import DBManager

    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"error": "选择账套后显示数据"}

    db = mgr.accounting

    # Bank balance (code starts with 1002)
    bank_balance = 0.0
    bank_accounts = [a for a in db.list_accounts() if a["code"].startswith("1002") and a["is_leaf"]]
    for acct in bank_accounts:
        bal = db.get_account_balance(acct["code"])
        bank_balance += bal["balance"]

    # Receivable (1122)
    receivable = 0.0
    recv_accounts = [a for a in db.list_accounts() if a["code"].startswith("1122") and a["is_leaf"]]
    for acct in recv_accounts:
        bal = db.get_account_balance(acct["code"])
        receivable += bal["balance"]

    # Payable (2202)
    payable = 0.0
    pay_accounts = [a for a in db.list_accounts() if a["code"].startswith("2202") and a["is_leaf"]]
    for acct in pay_accounts:
        bal = db.get_account_balance(acct["code"])
        payable += bal["balance"]

    # Monthly income/expense (from current period posted vouchers)
    from datetime import date as date_mod
    today = date_mod.today()
    period_id = f"{today.year}-{today.month:02d}"

    monthly_income = 0.0
    monthly_expense = 0.0

    income_accounts = db.list_accounts(category="income")
    for acct in income_accounts:
        if not acct["is_leaf"]:
            continue
        details = db.get_account_details(acct["code"], period_id=period_id)
        for d in details:
            monthly_income += d["credit"] - d["debit"]

    expense_accounts = db.list_accounts(category="expense")
    for acct in expense_accounts:
        if not acct["is_leaf"]:
            continue
        details = db.get_account_details(acct["code"], period_id=period_id)
        for d in details:
            monthly_expense += d["debit"] - d["credit"]

    # Draft voucher count
    drafts = db.list_vouchers(status="draft", limit=999)
    draft_count = len(drafts)

    return {
        "bank_balance": bank_balance,
        "receivable": receivable,
        "payable": payable,
        "monthly_income": monthly_income,
        "monthly_expense": monthly_expense,
        "draft_count": draft_count,
        "period": period_id,
    }


# =========================================================================
# MCP Status API
# =========================================================================

@app.get("/api/skills/list")
async def skills_list_api():
    """Return list of available skills for the UI capabilities panel."""
    try:
        from accobot.skills.loader import scan_skills
        skills = scan_skills()
        return {"skills": [{"name": s["name"], "description": s["description"], "category": s.get("category", "")} for s in skills]}
    except Exception as e:
        return {"skills": [], "error": str(e)}


@app.get("/api/mcp/status")
async def mcp_status():
    """Return status of configured MCP servers."""
    try:
        from accobot.mcp.client import get_mcp_status
        servers = get_mcp_status()
        return {"servers": servers}
    except ImportError:
        return {"servers": [], "note": "MCP SDK not installed (pip install 'accobot[mcp]')"}
    except Exception as e:
        return {"servers": [], "error": str(e)}


@app.post("/api/mcp/reconnect")
async def mcp_reconnect(request: dict):
    """Reconnect a specific MCP server."""
    try:
        from accobot.mcp.client import reconnect_server
        name = request.get("name", "")
        if not name:
            return {"success": False, "error": "请指定服务器名称"}
        ok = reconnect_server(name)
        if ok:
            return {"success": True, "message": f"MCP server '{name}' 已重连"}
        return {"success": False, "error": f"MCP server '{name}' 重连失败"}
    except ImportError:
        return {"success": False, "error": "MCP SDK 未安装"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/mcp/add")
async def mcp_add_server(request: dict):
    """Add a new MCP server via Web UI."""
    from accobot.config import load_config, save_config

    name = request.get("name", "").strip()
    if not name:
        return {"success": False, "error": "服务器名称不能为空"}

    config = load_config()
    if "mcp_servers" not in config:
        config["mcp_servers"] = {}

    if name in config["mcp_servers"]:
        return {"success": False, "error": f"服务器 '{name}' 已存在"}

    server_type = request.get("type", "stdio")
    new_server = {"enabled": True, "timeout": 120}

    if server_type == "http":
        url = request.get("url", "").strip()
        if not url:
            return {"success": False, "error": "请输入服务器 URL"}
        new_server["url"] = url
    else:
        command = request.get("command", "").strip()
        if not command:
            return {"success": False, "error": "请输入命令"}
        new_server["command"] = command
        args_str = request.get("args", "").strip()
        if args_str:
            new_server["args"] = [a.strip() for a in args_str.split(",") if a.strip()]

    config["mcp_servers"][name] = new_server
    save_config(config)

    return {"success": True, "message": f"MCP 服务器 '{name}' 已添加，刷新页面后生效"}


@app.post("/api/mcp/remove")
async def mcp_remove_server(request: dict):
    """Remove an MCP server via Web UI."""
    from accobot.config import load_config, save_config

    name = request.get("name", "").strip()
    if not name:
        return {"success": False, "error": "请指定服务器名称"}
    if name == "playwright":
        return {"success": False, "error": "Playwright 是内置服务器，不能删除（可以禁用）"}

    config = load_config()
    servers = config.get("mcp_servers", {})
    if name not in servers:
        return {"success": False, "error": f"服务器 '{name}' 不存在"}

    del servers[name]
    save_config(config)
    return {"success": True, "message": f"MCP 服务器 '{name}' 已删除"}


@app.post("/api/mcp/toggle")
async def mcp_toggle_server(request: dict):
    """Enable/disable an MCP server via Web UI."""
    from accobot.config import load_config, save_config

    name = request.get("name", "").strip()
    enabled = request.get("enabled", True)

    config = load_config()
    servers = config.get("mcp_servers", {})
    if name not in servers:
        return {"success": False, "error": f"服务器 '{name}' 不存在"}

    servers[name]["enabled"] = enabled
    save_config(config)
    status = "启用" if enabled else "禁用"
    return {"success": True, "message": f"MCP 服务器 '{name}' 已{status}"}


# =========================================================================
# Gateway Configuration API
# =========================================================================

@app.get("/api/config/gateway")
async def get_gateway_config():
    """Return gateway platform configuration (secrets redacted)."""
    from accobot.config import get_env_path
    env_path = get_env_path()
    env_vars = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                env_vars[key.strip()] = val.strip()

    return {
        "wecom": {
            "corp_id": env_vars.get("WECOM_CORP_ID", ""),
            "agent_id": env_vars.get("WECOM_AGENT_ID", ""),
            "secret": bool(env_vars.get("WECOM_SECRET", "")),
        },
        "dingtalk": {
            "app_key": env_vars.get("DINGTALK_APP_KEY", ""),
            "secret": bool(env_vars.get("DINGTALK_APP_SECRET", "")),
        },
        "feishu": {
            "app_id": env_vars.get("FEISHU_APP_ID", ""),
            "secret": bool(env_vars.get("FEISHU_APP_SECRET", "")),
        },
    }


@app.post("/api/config/gateway")
async def save_gateway_config(request: dict):
    """Save gateway platform configuration to .env file."""
    from accobot.config import get_env_path, ensure_home

    ensure_home()
    env_path = get_env_path()

    # Read existing .env
    existing_lines = []
    if env_path.exists():
        existing_lines = env_path.read_text(encoding="utf-8").splitlines()

    # Map of env var names to new values
    updates = {}
    wecom = request.get("wecom", {})
    if wecom.get("corp_id") is not None:
        updates["WECOM_CORP_ID"] = wecom["corp_id"]
    if wecom.get("agent_id") is not None:
        updates["WECOM_AGENT_ID"] = wecom["agent_id"]
    if wecom.get("secret") is not None:
        updates["WECOM_SECRET"] = wecom["secret"]

    dingtalk = request.get("dingtalk", {})
    if dingtalk.get("app_key") is not None:
        updates["DINGTALK_APP_KEY"] = dingtalk["app_key"]
    if dingtalk.get("secret") is not None:
        updates["DINGTALK_APP_SECRET"] = dingtalk["secret"]

    feishu = request.get("feishu", {})
    if feishu.get("app_id") is not None:
        updates["FEISHU_APP_ID"] = feishu["app_id"]
    if feishu.get("secret") is not None:
        updates["FEISHU_APP_SECRET"] = feishu["secret"]

    # Apply updates to existing lines
    updated_keys = set()
    for i, line in enumerate(existing_lines):
        if "=" in line and not line.startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in updates:
                existing_lines[i] = f"{key}={updates[key]}"
                updated_keys.add(key)

    # Append new keys
    for key, val in updates.items():
        if key not in updated_keys and val:
            existing_lines.append(f"{key}={val}")

    env_path.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")

    # Reload env vars
    for key, val in updates.items():
        if val:
            os.environ[key] = val

    return {"success": True, "message": "平台配置已保存"}


# =========================================================================
# Config API — Accounts, Auxiliary Items, Periods
# =========================================================================

@app.get("/api/accounts")
async def get_accounts_api(category: str = None, keyword: str = None):
    """List accounts with optional filters."""
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"accounts": [], "error": "未选择账套"}
    if keyword:
        accounts = mgr.accounting.search_accounts(keyword)
    else:
        accounts = mgr.accounting.list_accounts(category=category)
    return {"accounts": [dict(a) for a in accounts], "count": len(accounts)}


@app.get("/api/accounts/tree")
async def get_accounts_tree():
    """Return accounts as a tree structure."""
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"tree": [], "error": "未选择账套"}
    accounts = mgr.accounting.list_accounts()
    # Build tree
    by_code = {a["code"]: {**a, "children": []} for a in accounts}
    tree = []
    for a in accounts:
        node = by_code[a["code"]]
        parent = a.get("parent_code")
        if parent and parent in by_code:
            by_code[parent]["children"].append(node)
        else:
            tree.append(node)
    return {"tree": tree}


@app.get("/api/aux-items")
async def get_aux_items_api(type: str = None):
    """List auxiliary accounting items."""
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"items": [], "error": "未选择账套"}
    with mgr.accounting._lock:
        sql = "SELECT * FROM aux_items WHERE is_active = 1"
        params = []
        if type:
            sql += " AND type = ?"
            params.append(type)
        sql += " ORDER BY type, code"
        cur = mgr.accounting._conn.execute(sql, params)
        items = [dict(row) for row in cur.fetchall()]
    return {"items": items, "count": len(items)}


@app.get("/api/periods")
async def get_periods_api():
    """List accounting periods."""
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"periods": [], "error": "未选择账套"}
    periods = mgr.accounting.list_periods()
    return {"periods": [dict(p) for p in periods], "count": len(periods)}


@app.get("/api/company/info")
async def get_company_info():
    """Get current company details."""
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    cid = mgr.current_company_id
    if not cid:
        return {"error": "未选择账套", "company": None}
    company = mgr.master.get_company(cid)
    return {"company": company}


@app.get("/api/user/profile")
async def get_user_profile():
    """Get user profile (role, name)."""
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    profile = mgr.master.get_user_profile()
    return {"profile": profile}


@app.post("/api/user/profile")
async def set_user_profile(request: dict):
    """Set user profile (role selection)."""
    from accobot.db.manager import DBManager
    role = request.get("role", "").strip()
    name = request.get("name", "").strip()
    if role not in ("boss", "accountant", "agency"):
        return {"success": False, "error": "角色必须是：boss/accountant/agency"}
    mgr = DBManager.get_instance()
    mgr.master.set_user_profile(role, name)
    return {"success": True, "role": role}


@app.get("/api/todos")
async def get_todos():
    """Return todo/reminder items grouped by category."""
    from datetime import date
    from accobot.db.manager import DBManager

    today = date.today()
    mgr = DBManager.get_instance()
    accounting_todos = []
    tax_todos = []
    business_todos = []
    social_todos = []

    # Check if there's an active company
    if mgr.accounting:
        # Accounting todos
        draft_vouchers = mgr.accounting.list_vouchers(status="draft", limit=100)
        if draft_vouchers:
            accounting_todos.append({
                "title": f"{len(draft_vouchers)} 张凭证待审核",
                "due_date": "尽快处理",
                "overdue": False,
            })

        # Check if current period needs closing
        current_period = mgr.accounting.get_current_period()
        if current_period and current_period["month"] < today.month:
            accounting_todos.append({
                "title": f"{current_period['year']}年{current_period['month']}月待结账",
                "due_date": "尽快处理",
                "overdue": True,
            })
    else:
        accounting_todos.append({
            "title": "请先创建或选择账套",
            "due_date": "",
            "overdue": False,
        })

    # Tax todos (calendar-based)
    day = today.day
    month = today.month

    if day <= 15:
        tax_todos.append({
            "title": "增值税申报",
            "due_date": f"{month}月15日",
            "overdue": False,
        })
        tax_todos.append({
            "title": "个税申报",
            "due_date": f"{month}月15日",
            "overdue": False,
        })
    else:
        # Already past deadline this month
        pass

    # Quarterly income tax (months 1,4,7,10)
    if month in (1, 4, 7, 10) and day <= 15:
        tax_todos.append({
            "title": "企业所得税季度预缴",
            "due_date": f"{month}月15日",
            "overdue": False,
        })

    # Business todos
    if month <= 6:
        tax_todos_overdue = month == 6 and day > 25
        business_todos.append({
            "title": "工商年报公示",
            "due_date": "6月30日前",
            "overdue": tax_todos_overdue,
        })

    # Social insurance
    if day <= 25:
        social_todos.append({
            "title": "社保缴费",
            "due_date": f"{month}月25日",
            "overdue": False,
        })

    return {
        "accounting": accounting_todos,
        "tax": tax_todos,
        "business": business_todos,
        "social": social_todos,
    }


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat."""
    await websocket.accept()

    load_env()
    config = load_config()

    # Create agent for this session
    try:
        agent = AccoAgent(config=config)
    except ValueError as e:
        await websocket.send_json({"type": "error", "content": str(e)})
        await websocket.close()
        return

    # Stop flag for interrupting agent turns
    stop_requested = {"value": False}

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            msg = json.loads(data)

            # Handle stop request
            if msg.get("type") == "stop":
                stop_requested["value"] = True
                await websocket.send_json({"type": "done"})
                continue

            user_message = msg.get("message", "")
            if not user_message:
                continue

            # Reset stop flag for new turn
            stop_requested["value"] = False

            # Run agent in thread pool to not block event loop
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

    # Add user message to history
    agent.messages.append({"role": "user", "content": user_message})

    iteration = 0
    while iteration < agent.max_iterations:
        iteration += 1

        # Check stop flag
        if stop_requested["value"]:
            agent.messages.append({"role": "assistant", "content": "（已被用户中断）"})
            await websocket.send_json({"type": "done"})
            return

        # Get tool definitions
        tool_defs = registry.get_definitions()

        kwargs = {
            "model": agent.model,
            "messages": agent.messages,
        }
        if tool_defs:
            kwargs["tools"] = tool_defs
            kwargs["tool_choice"] = "auto"

        try:
            # Stream response
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

            # Process tool calls if any
            if tool_calls_data:
                # Build assistant message
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

                # Execute each tool call
                for idx in sorted(tool_calls_data.keys()):
                    tc = tool_calls_data[idx]
                    name = tc["name"]
                    try:
                        args = json.loads(tc["arguments"])
                    except json.JSONDecodeError:
                        args = {}

                    # Notify client about tool call
                    await websocket.send_json({
                        "type": "tool_call",
                        "name": name,
                        "args": args,
                    })

                    # Execute tool
                    result = registry.dispatch(name, args)

                    # Notify client about tool result
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
                # No tool calls — final response
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

    # Max iterations
    await websocket.send_json({
        "type": "error",
        "content": "操作步骤较多，已达到单次对话的处理上限。",
    })


def start_server(host: str = "127.0.0.1", port: int = 9120, open_browser: bool = True):
    """Start the web server."""
    import uvicorn

    ensure_home()
    load_env()
    discover_tools()

    if open_browser:
        # Open browser after a short delay
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
