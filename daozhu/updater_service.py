"""
岛主 DaoZhu — 版本更新检查服务
启动时异步检查 Gitee/GitHub Release，发现新版本时通知用户。
检查点 URL 可在 config.json 中配置。
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from .config import PLATFORM_ROOT

logger = logging.getLogger(__name__)

CONFIG_FILE = PLATFORM_ROOT / "config.json"

# 当前版本（从 pyproject.toml 读取）
def _read_current_version() -> str:
    toml_path = PLATFORM_ROOT / "pyproject.toml"
    if toml_path.exists():
        for line in toml_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("version"):
                try:
                    return line.split('"')[1]
                except IndexError:
                    pass
    return "0.0.0"

CURRENT_VERSION = _read_current_version()

# 默认检查点（Gitee Release API）
DEFAULT_CHECK_URL = "https://gitee.com/api/v5/repos/yumen2278/DaoZhu/releases/latest"

# 缓存在内存中的检查结果
_last_check_result = None
_last_check_time: datetime | None = None
CHECK_INTERVAL = timedelta(hours=6)  # 每 6 小时检查一次


def _get_config() -> dict:
    """读取 config.json"""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_config(config: dict):
    """写回 config.json"""
    CONFIG_FILE.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _semver_compare(v1: str, v2: str) -> int:
    """语义化版本比较：v1 > v2 返回 1，相等返回 0，v1 < v2 返回 -1"""
    try:
        parts1 = [int(x) for x in v1.lstrip("v").split(".")]
        parts2 = [int(x) for x in v2.lstrip("v").split(".")]
        # 补齐到相同长度
        while len(parts1) < len(parts2):
            parts1.append(0)
        while len(parts2) < len(parts1):
            parts2.append(0)
        for a, b in zip(parts1, parts2):
            if a > b:
                return 1
            if a < b:
                return -1
        return 0
    except (ValueError, AttributeError):
        return 0


def get_check_url() -> str:
    """获取配置的检查点 URL"""
    config = _get_config()
    return config.get("updater", {}).get("check_url", DEFAULT_CHECK_URL)


def set_check_url(url: str):
    """设置检查点 URL"""
    config = _get_config()
    if "updater" not in config:
        config["updater"] = {}
    config["updater"]["check_url"] = url
    _save_config(config)


async def check_for_update() -> dict:
    """检查是否有新版本

    Returns:
        {
            "has_update": bool,
            "current_version": str,
            "latest_version": str | None,
            "release_url": str | None,
            "release_notes": str | None,
            "error": str | None,
        }
    """
    global _last_check_result, _last_check_time

    # 缓存检查（避免频繁请求）
    now = datetime.now()
    if _last_check_result is not None and _last_check_time is not None:
        if now - _last_check_time < CHECK_INTERVAL:
            return _last_check_result

    check_url = get_check_url()
    result = {
        "has_update": False,
        "current_version": CURRENT_VERSION,
        "latest_version": None,
        "release_url": None,
        "release_notes": None,
        "error": None,
    }

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(check_url, headers={
                "Accept": "application/json",
                "User-Agent": "DaoZhu/1.0",
            })
            if resp.status_code != 200:
                result["error"] = f"HTTP {resp.status_code}"
                _last_check_result = result
                _last_check_time = now
                return result

            data = resp.json()

            # 解析版本号（Gitee 和 GitHub 都用 tag_name）
            tag = data.get("tag_name", "")
            latest_ver = tag.lstrip("v")

            # 比对版本
            cmp = _semver_compare(CURRENT_VERSION, latest_ver)
            if cmp < 0:
                result["has_update"] = True
                result["latest_version"] = latest_ver
                result["release_url"] = data.get("html_url", str(check_url))
                result["release_notes"] = (data.get("body") or "")[:500]
            else:
                result["latest_version"] = latest_ver

            _last_check_result = result
            _last_check_time = now
            return result

    except httpx.ConnectError:
        result["error"] = "网络不可达"
    except httpx.TimeoutException:
        result["error"] = "请求超时"
    except json.JSONDecodeError:
        result["error"] = "响应格式错误"
    except Exception as e:
        result["error"] = str(e)

    _last_check_result = result
    _last_check_time = now
    return result


def get_cached_result() -> dict | None:
    """获取缓存的检查结果（不发起新请求）"""
    return _last_check_result
