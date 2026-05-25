"""
岛主 DaoZhu — 工作区进程管理器
职责: 发现、启停、健康检查、端口分配、状态管理
"""

import asyncio
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx

from .config import get_workspace_dir, get_port_range


class StartMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"
    ON_DEMAND = "on-demand"


class WorkspaceStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    CRASHED = "crashed"
    HIDDEN = "hidden"


@dataclass
class WorkspaceInfo:
    """工作区元信息 + 运行时状态"""
    id: str
    name: str
    icon: str = "📦"
    color: str = "#6366F1"
    version: str = "1.0.0"
    description: str = ""
    port: int = 0
    entry: str = "app.py"
    python: str = ".venv"
    tags: list[str] = field(default_factory=list)
    start_mode: str = "manual"
    hidden: bool = False
    source: str = "self-built"
    sort_order: int = 99

    # 运行时状态（不持久化）
    status: WorkspaceStatus = WorkspaceStatus.STOPPED
    process: Optional[subprocess.Popen] = field(default=None, repr=False)
    restart_count: int = 0
    last_health_check: float = 0.0

    @property
    def path(self) -> Path:
        return get_workspace_dir() / self.id

    def to_dict(self) -> dict:
        """转为前端 API 响应格式"""
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "color": self.color,
            "version": self.version,
            "description": self.description,
            "port": self.port,
            "tags": self.tags,
            "start_mode": self.start_mode,
            "status": self.status.value,
            "source": self.source,
            "sort_order": self.sort_order,
        }


class WorkspaceManager:
    """工作区进程管理器（单例）"""

    MAX_RESTART = 3
    HEALTH_CHECK_INTERVAL = 30  # 秒
    STOP_TIMEOUT = 5  # 秒

    def __init__(self):
        self.workspaces: dict[str, WorkspaceInfo] = {}
        self._used_ports: set[int] = set()
        self._health_task: Optional[asyncio.Task] = None

    # === 发现 ===

    def discover(self) -> list[WorkspaceInfo]:
        """扫描 workspaces/ 目录，发现所有工作区"""
        workspace_dir = get_workspace_dir()
        self.workspaces.clear()

        if not workspace_dir.exists():
            workspace_dir.mkdir(parents=True, exist_ok=True)
            return []

        for item in sorted(workspace_dir.iterdir()):
            if not item.is_dir():
                continue
            json_file = item / "workspace.json"
            if not json_file.exists():
                continue
            try:
                info = self._load_workspace(json_file)
                if info.hidden:
                    info.status = WorkspaceStatus.HIDDEN
                self.workspaces[info.id] = info
            except (json.JSONDecodeError, KeyError, OSError):
                continue

        return list(self.workspaces.values())

    def _load_workspace(self, json_path: Path) -> WorkspaceInfo:
        """从 workspace.json 加载工作区信息"""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return WorkspaceInfo(
            id=data["id"],
            name=data.get("name", data["id"]),
            icon=data.get("icon", "📦"),
            color=data.get("color", "#6366F1"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            port=data.get("port", 0),
            entry=data.get("entry", "app.py"),
            python=data.get("python", ".venv"),
            tags=data.get("tags", []),
            start_mode=data.get("start_mode", "manual"),
            hidden=data.get("hidden", False),
            source=data.get("source", "self-built"),
            sort_order=data.get("sort_order", 99),
        )

    # === 端口分配 ===

    def _allocate_port(self, workspace: WorkspaceInfo) -> int:
        """为工作区分配可用端口"""
        if workspace.port and workspace.port not in self._used_ports:
            if self._is_port_available(workspace.port):
                self._used_ports.add(workspace.port)
                return workspace.port

        port_min, port_max = get_port_range()
        for port in range(port_min, port_max + 1):
            if port not in self._used_ports and self._is_port_available(port):
                self._used_ports.add(port)
                return port

        raise RuntimeError(f"无可用端口 ({port_min}-{port_max})")

    @staticmethod
    def _is_port_available(port: int) -> bool:
        """检查端口是否可用"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return True
            except OSError:
                return False

    # === 启停 ===

    async def start_workspace(self, workspace_id: str) -> WorkspaceInfo:
        """启动工作区"""
        ws = self.workspaces.get(workspace_id)
        if not ws:
            raise ValueError(f"工作区不存在: {workspace_id}")

        if ws.status == WorkspaceStatus.RUNNING:
            return ws

        ws.status = WorkspaceStatus.STARTING
        ws.port = self._allocate_port(ws)

        try:
            ws.process = self._spawn_process(ws)
            # 等待启动完成
            await self._wait_for_ready(ws, timeout=15)
            ws.status = WorkspaceStatus.RUNNING
            ws.restart_count = 0
        except Exception as e:
            ws.status = WorkspaceStatus.CRASHED
            raise RuntimeError(f"启动失败: {e}")

        return ws

    def _spawn_process(self, ws: WorkspaceInfo) -> subprocess.Popen:
        """以 subprocess 启动工作区 FastAPI 服务"""
        workspace_path = ws.path

        # 确定 Python 解释器路径
        venv_path = Path(ws.python)
        if venv_path.is_absolute():
            # 绝对路径（如 AccoBot 的 venv）
            venv_python = venv_path / "Scripts" / "python.exe"
        else:
            # 相对路径（工作区内的 .venv）
            venv_python = workspace_path / ws.python / "Scripts" / "python.exe"

        if not venv_python.exists():
            # 尝试项目主 .venv
            from .config import PLATFORM_ROOT
            main_venv = PLATFORM_ROOT / ".venv" / "Scripts" / "python.exe"
            if main_venv.exists():
                venv_python = main_venv
            else:
                venv_python = Path(sys.executable)

        cmd = [
            str(venv_python), "-m", "uvicorn",
            f"{ws.entry.replace('.py', '')}:app",
            "--host", "127.0.0.1",
            "--port", str(ws.port),
        ]

        return subprocess.Popen(
            cmd,
            cwd=str(workspace_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

    async def _wait_for_ready(self, ws: WorkspaceInfo, timeout: int = 15):
        """等待工作区 HTTP 服务就绪"""
        start = time.time()
        url = f"http://127.0.0.1:{ws.port}/"

        async with httpx.AsyncClient() as client:
            while time.time() - start < timeout:
                try:
                    resp = await client.get(url, timeout=2)
                    if resp.status_code < 500:
                        return
                except (httpx.ConnectError, httpx.ReadTimeout):
                    pass

                # 检查进程是否已退出
                if ws.process and ws.process.poll() is not None:
                    raise RuntimeError("进程已退出")

                await asyncio.sleep(0.5)

        raise TimeoutError(f"工作区 {ws.id} 启动超时 ({timeout}s)")

    async def stop_workspace(self, workspace_id: str) -> WorkspaceInfo:
        """停止工作区"""
        ws = self.workspaces.get(workspace_id)
        if not ws:
            raise ValueError(f"工作区不存在: {workspace_id}")

        if ws.status != WorkspaceStatus.RUNNING:
            return ws

        if ws.process:
            ws.process.terminate()
            try:
                ws.process.wait(timeout=self.STOP_TIMEOUT)
            except subprocess.TimeoutExpired:
                ws.process.kill()
                ws.process.wait()
            ws.process = None

        if ws.port in self._used_ports:
            self._used_ports.discard(ws.port)

        ws.status = WorkspaceStatus.STOPPED
        return ws

    # === 隐藏/取消隐藏 ===

    def hide_workspace(self, workspace_id: str) -> None:
        """隐藏工作区（软删除）"""
        ws = self.workspaces.get(workspace_id)
        if not ws:
            raise ValueError(f"工作区不存在: {workspace_id}")
        ws.hidden = True
        ws.status = WorkspaceStatus.HIDDEN
        self._save_workspace_json(ws)

    def unhide_workspace(self, workspace_id: str) -> None:
        """取消隐藏工作区"""
        ws = self.workspaces.get(workspace_id)
        if not ws:
            raise ValueError(f"工作区不存在: {workspace_id}")
        ws.hidden = False
        ws.status = WorkspaceStatus.STOPPED
        self._save_workspace_json(ws)

    def _save_workspace_json(self, ws: WorkspaceInfo) -> None:
        """更新 workspace.json"""
        json_path = ws.path / "workspace.json"
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["hidden"] = ws.hidden
        data["start_mode"] = ws.start_mode
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # === 健康检查 ===

    async def health_check(self) -> None:
        """对所有运行中的工作区执行健康检查"""
        async with httpx.AsyncClient() as client:
            for ws in self.workspaces.values():
                if ws.status != WorkspaceStatus.RUNNING:
                    continue
                await self._check_one(ws, client)

    async def _check_one(self, ws: WorkspaceInfo, client: httpx.AsyncClient):
        """检查单个工作区健康状态"""
        # 检查进程是否存活
        if ws.process and ws.process.poll() is not None:
            await self._handle_crash(ws)
            return

        # HTTP 健康检查
        try:
            resp = await client.get(
                f"http://127.0.0.1:{ws.port}/",
                timeout=5,
            )
            if resp.status_code >= 500:
                await self._handle_crash(ws)
        except (httpx.ConnectError, httpx.ReadTimeout):
            await self._handle_crash(ws)

        ws.last_health_check = time.time()

    async def _handle_crash(self, ws: WorkspaceInfo):
        """处理工作区崩溃：自动重启或标记 crashed"""
        ws.restart_count += 1
        if ws.restart_count <= self.MAX_RESTART:
            ws.status = WorkspaceStatus.STOPPED
            try:
                await self.start_workspace(ws.id)
            except Exception:
                ws.status = WorkspaceStatus.CRASHED
        else:
            ws.status = WorkspaceStatus.CRASHED

    # === 生命周期 ===

    async def startup(self) -> None:
        """平台启动时调用：发现工作区 + 启动 auto 模式的"""
        self.discover()

        # 启动 auto 模式的工作区
        for ws in self.workspaces.values():
            if ws.start_mode == StartMode.AUTO and ws.status != WorkspaceStatus.HIDDEN:
                try:
                    await self.start_workspace(ws.id)
                except Exception:
                    pass  # 启动失败不阻塞平台

        # 启动健康检查循环
        self._health_task = asyncio.create_task(self._health_loop())

    async def shutdown(self) -> None:
        """平台关闭时调用：停止所有工作区"""
        if self._health_task:
            self._health_task.cancel()

        for ws in list(self.workspaces.values()):
            if ws.status == WorkspaceStatus.RUNNING:
                try:
                    await self.stop_workspace(ws.id)
                except Exception:
                    # 强制杀掉
                    if ws.process:
                        ws.process.kill()
                        ws.process = None

    async def _health_loop(self):
        """后台健康检查循环"""
        while True:
            await asyncio.sleep(self.HEALTH_CHECK_INTERVAL)
            try:
                await self.health_check()
            except Exception:
                pass

    # === 查询 ===

    def list_workspaces(self, include_hidden: bool = False) -> list[dict]:
        """返回工作区列表（前端 API 用），按 sort_order 排序"""
        result = []
        for ws in self.workspaces.values():
            if ws.status == WorkspaceStatus.HIDDEN and not include_hidden:
                continue
            result.append(ws.to_dict())
        result.sort(key=lambda x: x.get("sort_order", 99))
        return result

    def get_workspace(self, workspace_id: str) -> Optional[WorkspaceInfo]:
        """获取单个工作区信息"""
        return self.workspaces.get(workspace_id)


# 全局单例
manager = WorkspaceManager()
