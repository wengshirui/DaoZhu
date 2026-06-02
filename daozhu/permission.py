"""
岛主 DaoZhu — 工具调用权限门控（Permission Gate）
参考: DeepSeek-Reasonix internal/permission/
职责: 每次工具调用前检查 allow / ask / deny 规则
"""

import fnmatch
import json
from typing import Literal

from .config import get_config_value

# 默认规则（用户未配置时使用）
DEFAULT_ALLOW_PATTERNS = [
    "web_search(*)",
    "list_workspaces(*)",
    "call_workspace_api(GET *)",
    "get_workspace_readme(*)",
]

DEFAULT_DENY_PATTERNS = [
    "terminal(rm -rf*)",
    "terminal(del /s*)",
    "terminal(format*)",
    "terminal(rmdir /s*)",
    "write_file(C:\\Windows*)",
    "write_file(C:\\Program Files*)",
]


def _get_permission_config() -> dict:
    """读取权限配置"""
    return {
        "default": get_config_value("permissions.default", "allow"),
        "allow": get_config_value("permissions.allow", DEFAULT_ALLOW_PATTERNS),
        "deny": get_config_value("permissions.deny", DEFAULT_DENY_PATTERNS),
    }


def _build_call_signature(tool_name: str, args: dict) -> str:
    """构建工具调用签名字符串，用于模式匹配"""
    # 简单策略：tool_name(关键参数值)
    if not args:
        return f"{tool_name}()"

    # 取第一个有意义的参数值作为匹配目标
    # 对于不同工具有不同的关键参数
    key_params = {
        "terminal": "command",
        "write_file": "path",
        "read_file": "path",
        "delete_file": "path",
        "web_search": "query",
        "call_workspace_api": "method",
        "run_python": "code",
    }

    key = key_params.get(tool_name)
    if key and key in args:
        return f"{tool_name}({args[key]})"

    # 默认：用所有参数值拼接
    values = " ".join(str(v) for v in args.values() if v)
    return f"{tool_name}({values[:100]})"


def check_permission(tool_name: str, args: dict) -> Literal["allow", "ask", "deny"]:
    """
    检查工具调用权限。
    返回: "allow"（静默放行）/ "ask"（需要用户确认）/ "deny"（拒绝执行）
    """
    config = _get_permission_config()
    signature = _build_call_signature(tool_name, args)

    # 1. 先检查 deny（优先级最高）
    for pattern in config["deny"]:
        if fnmatch.fnmatch(signature, pattern):
            return "deny"

    # 2. 再检查 allow
    for pattern in config["allow"]:
        if fnmatch.fnmatch(signature, pattern):
            return "allow"

    # 3. 未匹配任何规则，走默认行为
    return config["default"]
