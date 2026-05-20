"""File tools — read, write, and search files.

Toolset: "file"
Provides the agent with file system access for reading bank statements,
writing export files, and searching documents.

Simplified from Hermes Agent's file_tools.py — same API surface, less complexity.
"""

import json
import os
from pathlib import Path
from accobot.tools.registry import registry, tool_result, tool_error


def _resolve_path(filepath: str) -> Path:
    """Resolve a file path (supports ~, relative, absolute)."""
    p = Path(os.path.expanduser(filepath))
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def _is_binary_extension(path: Path) -> bool:
    """Check if a file has a binary extension."""
    binary_exts = {
        ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
        ".zip", ".tar", ".gz", ".7z", ".rar",
        ".db", ".sqlite", ".sqlite3",
        ".pyc", ".pyo", ".class",
        ".woff", ".woff2", ".ttf", ".otf",
        ".mp3", ".mp4", ".avi", ".mov", ".wav",
    }
    return path.suffix.lower() in binary_exts


# =========================================================================
# Read File
# =========================================================================

def read_file(args: dict, **kwargs) -> str:
    """Read a text file with line numbers and pagination."""
    filepath = args.get("path", "")
    offset = max(1, int(args.get("offset", 1)))
    limit = min(2000, max(1, int(args.get("limit", 200))))

    if not filepath:
        return tool_error("请指定文件路径")

    path = _resolve_path(filepath)

    if not path.exists():
        return tool_error(f"文件不存在：{filepath}")
    if not path.is_file():
        return tool_error(f"不是文件：{filepath}")
    if _is_binary_extension(path):
        return tool_error(f"无法读取二进制文件：{path.suffix}")

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return tool_error(f"读取文件失败：{e}")

    lines = content.splitlines()
    total_lines = len(lines)

    # Pagination
    start = offset - 1
    end = start + limit
    selected = lines[start:end]

    # Format with line numbers
    numbered = []
    for i, line in enumerate(selected, start=offset):
        numbered.append(f"{i:4d}|{line}")

    result_content = "\n".join(numbered)
    truncated = end < total_lines

    return tool_result(
        content=result_content,
        path=str(path),
        total_lines=total_lines,
        lines_shown=len(selected),
        offset=offset,
        truncated=truncated,
        file_size=path.stat().st_size,
    )


# =========================================================================
# Write File
# =========================================================================

def write_file(args: dict, **kwargs) -> str:
    """Write content to a file (creates parent dirs automatically)."""
    filepath = args.get("path", "")
    content = args.get("content", "")

    if not filepath:
        return tool_error("请指定文件路径")
    if content is None:
        return tool_error("请提供文件内容")

    path = _resolve_path(filepath)

    # Safety: don't overwrite system files
    dangerous_prefixes = ("/etc", "/usr", "/bin", "/sbin", "C:\\Windows")
    for prefix in dangerous_prefixes:
        if str(path).startswith(prefix):
            return tool_error(f"安全限制：不允许写入系统目录 {prefix}")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except Exception as e:
        return tool_error(f"写入文件失败：{e}")

    return tool_result(
        success=True,
        path=str(path),
        size=len(content.encode("utf-8")),
        message=f"✅ 已写入 {path.name}（{len(content)} 字符）",
    )


# =========================================================================
# List Directory
# =========================================================================

def list_directory(args: dict, **kwargs) -> str:
    """List files in a directory."""
    dirpath = args.get("path", ".")
    pattern = args.get("pattern", "*")

    path = _resolve_path(dirpath)

    if not path.exists():
        return tool_error(f"目录不存在：{dirpath}")
    if not path.is_dir():
        return tool_error(f"不是目录：{dirpath}")

    try:
        entries = sorted(path.glob(pattern))
    except Exception as e:
        return tool_error(f"列出目录失败：{e}")

    items = []
    for entry in entries[:100]:  # Limit to 100 entries
        if entry.name.startswith("."):
            continue
        item = {
            "name": entry.name,
            "type": "dir" if entry.is_dir() else "file",
        }
        if entry.is_file():
            item["size"] = entry.stat().st_size
        items.append(item)

    return tool_result(
        path=str(path),
        items=items,
        count=len(items),
        total=len(entries),
    )


# =========================================================================
# Registration
# =========================================================================

registry.register(
    name="read_file",
    toolset="file",
    schema={
        "name": "read_file",
        "description": "读取文本文件内容（带行号和分页）。用于读取银行流水文件、导出的报表、配置文件等。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径（支持绝对路径、相对路径、~/路径）"},
                "offset": {"type": "integer", "description": "起始行号（从1开始，默认1）", "default": 1},
                "limit": {"type": "integer", "description": "读取行数上限（默认200，最大2000）", "default": 200},
            },
            "required": ["path"],
        },
    },
    handler=read_file,
    emoji="📖",
)

registry.register(
    name="write_file",
    toolset="file",
    schema={
        "name": "write_file",
        "description": "写入文件（完全覆盖）。用于导出报表、生成申报表文件、保存分析结果等。自动创建父目录。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "要写入的完整内容"},
            },
            "required": ["path", "content"],
        },
    },
    handler=write_file,
    emoji="✍️",
)

registry.register(
    name="list_directory",
    toolset="file",
    schema={
        "name": "list_directory",
        "description": "列出目录中的文件和子目录。用于查看账套文件夹、原始单据目录等。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "目录路径（默认当前目录）", "default": "."},
                "pattern": {"type": "string", "description": "文件名匹配模式（如 *.xlsx）", "default": "*"},
            },
        },
    },
    handler=list_directory,
    emoji="📂",
)
