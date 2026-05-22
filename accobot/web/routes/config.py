"""Configuration & Company management routes."""

import os
from fastapi import APIRouter

from accobot.config import load_config, load_env, get_api_key

router = APIRouter()


@router.get("/api/status")
async def status():
    """Return system status."""
    from accobot import __version__
    from accobot.tools.registry import registry, discover_tools
    discover_tools()
    load_env()
    has_api_key = bool(get_api_key())
    return {
        "version": __version__,
        "tools": registry.get_all_tool_names(),
        "tool_count": len(registry.get_all_tool_names()),
        "has_api_key": has_api_key,
    }


@router.get("/api/config")
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


@router.post("/api/config/apikey")
async def save_api_key(request: dict):
    """Save API key to .env file."""
    from accobot.config import get_env_path, ensure_home
    key = request.get("api_key", "").strip()
    provider = request.get("provider", "deepseek").strip()

    if not key:
        return {"success": False, "error": "API Key 不能为空"}

    ensure_home()
    env_path = get_env_path()

    existing = ""
    if env_path.exists():
        existing = env_path.read_text(encoding="utf-8")

    env_var = "DEEPSEEK_API_KEY" if provider == "deepseek" else "OPENAI_API_KEY"

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
    os.environ[env_var] = key
    load_env()

    return {"success": True, "message": "API Key 已保存"}


@router.post("/api/config/model")
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


# =========================================================================
# Companies
# =========================================================================

@router.get("/api/companies")
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


@router.post("/api/companies/switch")
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


@router.post("/api/companies/create")
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


@router.post("/api/companies/open-folder")
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


@router.post("/api/companies/delete")
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
# Gateway Configuration
# =========================================================================

@router.get("/api/config/gateway")
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


@router.post("/api/config/gateway")
async def save_gateway_config(request: dict):
    """Save gateway platform configuration to .env file."""
    from accobot.config import get_env_path, ensure_home

    ensure_home()
    env_path = get_env_path()

    existing_lines = []
    if env_path.exists():
        existing_lines = env_path.read_text(encoding="utf-8").splitlines()

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

    updated_keys = set()
    for i, line in enumerate(existing_lines):
        if "=" in line and not line.startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in updates:
                existing_lines[i] = f"{key}={updates[key]}"
                updated_keys.add(key)

    for key, val in updates.items():
        if key not in updated_keys and val:
            existing_lines.append(f"{key}={val}")

    env_path.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")

    for key, val in updates.items():
        if val:
            os.environ[key] = val

    return {"success": True, "message": "平台配置已保存"}


# =========================================================================
# User Profile
# =========================================================================

@router.get("/api/company/info")
async def get_company_info():
    """Get current company details."""
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    cid = mgr.current_company_id
    if not cid:
        return {"error": "未选择账套", "company": None}
    company = mgr.master.get_company(cid)
    return {"company": company}


@router.get("/api/user/profile")
async def get_user_profile():
    """Get user profile (role, name)."""
    from accobot.db.manager import DBManager
    mgr = DBManager.get_instance()
    profile = mgr.master.get_user_profile()
    return {"profile": profile}


@router.post("/api/user/profile")
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
