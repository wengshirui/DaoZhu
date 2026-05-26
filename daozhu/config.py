"""
岛主 DaoZhu — 平台全局配置
职责: 读取/写入 config.json + .env，提供默认值合并机制
"""

import json
import os
from pathlib import Path
from typing import Any

# 平台根目录（daozhu/ 的上一级）
PLATFORM_ROOT = Path(__file__).parent.parent

# 配置文件路径
CONFIG_FILE = PLATFORM_ROOT / "config.json"
ENV_FILE = PLATFORM_ROOT / ".env"

# === 默认配置 ===
DEFAULT_CONFIG = {
    "platform": {
        "port": 7788,
        "workspace_dir": "./workspaces",
        "port_range": [7801, 7899],
    },
    "ai": {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
    },
    "display": {
        "theme": "light",
        "language": "zh-CN",
    },
}

# === 敏感配置（从 .env 读取）===
ENV_VARS = {
    "DEEPSEEK_API_KEY": {
        "description": "DeepSeek API 密钥",
        "required": False,
    },
    "OPENAI_API_KEY": {
        "description": "OpenAI API 密钥",
        "required": False,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并两个字典，override 覆盖 base"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_env_file(env_path: Path) -> dict[str, str]:
    """解析 .env 文件，返回键值对"""
    env_vars = {}
    if not env_path.exists():
        return env_vars

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                env_vars[key] = value
    return env_vars


def load_config() -> dict:
    """
    加载完整配置：DEFAULT_CONFIG + config.json 用户覆盖
    返回合并后的配置字典
    """
    user_config = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_config = json.load(f)
        except (json.JSONDecodeError, OSError):
            user_config = {}

    return _deep_merge(DEFAULT_CONFIG, user_config)


def save_config(config: dict) -> None:
    """保存用户配置到 config.json（只保存与默认值不同的部分）"""
    # 计算差异
    diff = _compute_diff(DEFAULT_CONFIG, config)
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(diff, f, ensure_ascii=False, indent=2)


def _compute_diff(default: dict, current: dict) -> dict:
    """计算 current 与 default 的差异"""
    diff = {}
    for key, value in current.items():
        if key not in default:
            diff[key] = value
        elif isinstance(value, dict) and isinstance(default.get(key), dict):
            sub_diff = _compute_diff(default[key], value)
            if sub_diff:
                diff[key] = sub_diff
        elif value != default.get(key):
            diff[key] = value
    return diff


def get_config_value(path: str, default: Any = None) -> Any:
    """
    通过点分路径获取配置值
    例: get_config_value("ai.provider") → "deepseek"
    """
    config = load_config()
    keys = path.split(".")
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def set_config_value(path: str, value: Any) -> None:
    """
    通过点分路径设置配置值
    例: set_config_value("display.theme", "dark")
    """
    config = load_config()
    keys = path.split(".")
    current = config
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value
    save_config(config)


def load_env() -> dict[str, str]:
    """加载 .env 文件中的环境变量"""
    env_vars = _load_env_file(ENV_FILE)
    # 同时检查系统环境变量（优先级更高）
    for key in ENV_VARS:
        sys_val = os.environ.get(key)
        if sys_val:
            env_vars[key] = sys_val
    return env_vars


def get_api_key(provider: str = None) -> str | None:
    """获取当前 AI 提供商的 API Key"""
    if provider is None:
        provider = get_config_value("ai.provider", "deepseek")

    key_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
    }

    env_key = key_map.get(provider)
    if not env_key:
        return None

    # 优先从 config.db 读取
    try:
        from .config_db import get_secret
        val = get_secret(env_key)
        if val:
            return val
    except Exception:
        pass

    # 降级：从 .env 读取
    env_vars = load_env()
    return env_vars.get(env_key)


def get_workspace_dir() -> Path:
    """获取工作区根目录的绝对路径"""
    workspace_dir = get_config_value("platform.workspace_dir", "./workspaces")
    path = Path(workspace_dir)
    if not path.is_absolute():
        path = PLATFORM_ROOT / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_port_range() -> tuple[int, int]:
    """获取工作区端口范围"""
    port_range = get_config_value("platform.port_range", [7801, 7899])
    return (port_range[0], port_range[1])
