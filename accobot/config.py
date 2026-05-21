"""Configuration management for AccoBot.

Layered config: config.yaml (settings) + .env (API keys).
Inspired by Hermes Agent's config system.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


def get_accobot_home() -> Path:
    """Return the AccoBot home directory (~/.accobot by default)."""
    env_home = os.environ.get("ACCOBOT_HOME")
    if env_home:
        return Path(env_home)
    return Path.home() / ".accobot"


def ensure_home() -> Path:
    """Ensure the AccoBot home directory exists and return it."""
    home = get_accobot_home()
    home.mkdir(parents=True, exist_ok=True)
    return home


DEFAULT_CONFIG: Dict[str, Any] = {
    "model": {
        "provider": "deepseek",
        "model_name": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "max_iterations": 90,
    },
    "agent": {
        "system_prompt_file": None,
        "temperature": 0.3,
    },
    "database": {
        "dir": None,  # defaults to ~/.accobot/data/
    },
    "web": {
        "host": "127.0.0.1",
        "port": 9120,
        "auto_open_browser": True,
    },
    "user": {
        "role": None,  # boss / accountant / agency
        "name": None,
    },
    "mcp_servers": {
        "playwright": {
            "command": "npx",
            "args": ["-y", "@playwright/mcp@latest"],
            "enabled": True,
            "timeout": 120,
        },
    },
    "heartbeat": {
        "enabled": True,
        "interval_minutes": 5,
    },
}


def get_config_path() -> Path:
    """Return path to config.yaml."""
    return get_accobot_home() / "config.yaml"


def get_env_path() -> Path:
    """Return path to .env file."""
    return get_accobot_home() / ".env"


def load_config() -> Dict[str, Any]:
    """Load config from config.yaml, merged with defaults."""
    config = _deep_copy(DEFAULT_CONFIG)
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        _deep_merge(config, user_config)
    return config


def save_config(config: Dict[str, Any]) -> None:
    """Save config to config.yaml."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def load_env() -> None:
    """Load .env file into environment."""
    env_path = get_env_path()
    if env_path.exists():
        load_dotenv(env_path)


def get_data_dir(config: Optional[Dict[str, Any]] = None) -> Path:
    """Return the data directory for database files."""
    if config and config.get("database", {}).get("dir"):
        return Path(config["database"]["dir"])
    return get_accobot_home() / "data"


def get_api_key(config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Get the API key from environment."""
    for key in ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ACCOBOT_API_KEY"]:
        val = os.environ.get(key)
        if val:
            return val
    return None


def _deep_copy(d: Dict) -> Dict:
    """Simple deep copy for nested dicts."""
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _deep_copy(v)
        elif isinstance(v, list):
            result[k] = v[:]
        else:
            result[k] = v
    return result


def _deep_merge(base: Dict, override: Dict) -> None:
    """Merge override into base (in-place), recursing into nested dicts."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
