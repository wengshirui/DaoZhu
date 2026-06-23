"""岛主 DaoZhu — 平台主服务
端口: 7788
职责: 应用生命周期 + 路由注册 + 入口点
路由按功能拆分到 routers/ 目录下。
"""

import os
# 确保本地连接不走系统代理（修复 Clash/代理环境下 httpx 502 问题）
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

# === 日志配置（按日期分文件）===
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

_log_handler = TimedRotatingFileHandler(
    LOG_DIR / "daozhu.log",
    when="midnight",
    interval=1,
    backupCount=30,  # 保留 30 天
    encoding="utf-8",
)
_log_handler.suffix = "%Y-%m-%d"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        _log_handler,
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("daozhu")
from fastapi.staticfiles import StaticFiles

from .config import get_config_value
from .workspace_manager import manager
from .chat_db import init_chat_db
from .memory_db import init_memory_db
from .routers import register_routers

# 静态文件目录（适配 PyInstaller 打包环境）
import sys
if getattr(sys, "frozen", False):
    FRONTEND_DIR = Path(sys._MEIPASS) / "daozhu" / "frontend"
else:
    FRONTEND_DIR = Path(__file__).parent / "frontend"


def _mount_lightweight_workspaces(the_app: FastAPI):
    """将 mode=lightweight 的工作区挂载为主进程子路由"""
    import importlib.util
    import sys as _sys
    from .workspace_manager import WorkspaceStatus
    for ws in manager.workspaces.values():
        if ws.mode != "lightweight":
            continue
        app_file = ws.path / ws.entry
        if not app_file.exists():
            continue
        try:
            ws_path_str = str(ws.path)
            for mod_name in list(_sys.modules.keys()):
                if mod_name == "routes" or mod_name.startswith("routes."):
                    del _sys.modules[mod_name]
                if mod_name == "db" or mod_name == "gitee_client":
                    del _sys.modules[mod_name]
            if ws_path_str not in _sys.path:
                _sys.path.insert(0, ws_path_str)
            spec = importlib.util.spec_from_file_location(f"ws_{ws.id}_app", str(app_file))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "app") and hasattr(mod.app, "routes"):
                the_app.mount(f"/ws/{ws.id}", mod.app)
                ws.status = WorkspaceStatus.RUNNING
                ws.port = 7788
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"轻挂载 {ws.id} 失败: {e}")
            ws.mode = "standard"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """平台生命周期：启动时发现工作区，关闭时清理"""
    logger.info("=" * 40)
    logger.info("岛主 DaoZhu 启动中...")
    init_chat_db()
    init_memory_db()
    from .config_db import init_config_db
    init_config_db()
    from .tool_log_db import init_tool_log_db
    init_tool_log_db()
    from .lifecycle_db import init_lifecycle_db, get_current_agent, birth_new_agent
    init_lifecycle_db()
    # 确保有存活的 agent（首次启动或前代已死亡时自动创建新一代）
    if not get_current_agent():
        birth_new_agent()
    await manager.startup()
    _mount_lightweight_workspaces(app)

    # 启动定时任务调度器
    from .scheduler import scheduler
    await scheduler.start()

    # Agent 成长检查
    from .growth import should_grow, run_growth
    if should_grow():
        try:
            run_growth()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"自动成长失败: {e}")

    # 启动时检查更新（异步，不阻塞启动）
    from .updater_service import check_for_update
    import asyncio
    try:
        asyncio.ensure_future(check_for_update())
    except Exception:
        pass

    yield

    await scheduler.stop()
    await manager.shutdown()


app = FastAPI(title="岛主 DaoZhu", version="0.1.0", lifespan=lifespan)

# 挂载静态文件
app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
app.mount("/img", StaticFiles(directory=str(FRONTEND_DIR / "img")), name="img")


# 宠物资源
_pets_dir = FRONTEND_DIR.parent.parent / "workspaces" / "desktop-pet" / "pets"
if _pets_dir.exists():
    app.mount("/pets", StaticFiles(directory=str(_pets_dir)), name="pet_assets")
# 注册所有路由
register_routers(app)


if __name__ == "__main__":
    import uvicorn
    port = get_config_value("platform.port", 7788)
    uvicorn.run(app, host="0.0.0.0", port=port)
