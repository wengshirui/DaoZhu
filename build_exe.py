"""Build AccoBot into a standalone Windows exe using PyInstaller.

Usage:
    python build_exe.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
ENTRY = ROOT / "accobot_web.py"
ICON = ROOT / "accobot" / "web" / "static" / "favicon.ico"

# Data files to bundle
datas = [
    # Web static files (HTML, JS, CSS)
    (str(ROOT / "accobot" / "web" / "static"), "accobot/web/static"),
    # Accounting standards (templates, rules)
    (str(ROOT / "accobot" / "standards"), "accobot/standards"),
    # Skills
    (str(ROOT / "accobot" / "skills"), "accobot/skills"),
]

# Hidden imports that PyInstaller might miss
hidden_imports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "accobot.web.routes",
    "accobot.web.routes.config",
    "accobot.web.routes.files",
    "accobot.web.routes.chat",
    "accobot.web.routes.ledger",
    "accobot.web.routes.mcp",
    "accobot.web.routes.todos",
    "accobot.db.manager",
    "accobot.db.master",
    "accobot.db.accounting",
    "accobot.db.chat_history",
    "accobot.db.standards",
    "accobot.db.templates",
    "accobot.tools.registry",
    "accobot.mcp.client",
    "accobot.skills.loader",
    "accobot.proactive",
]

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--name", "AccoBot",
    "--onefile",
    "--console",
    "--noconfirm",
    "--clean",
]

# Add icon if exists
if ICON.exists():
    cmd += ["--icon", str(ICON)]

# Add data files
for src, dest in datas:
    if Path(src).exists():
        cmd += ["--add-data", f"{src};{dest}"]

# Add hidden imports
for hi in hidden_imports:
    cmd += ["--hidden-import", hi]

# Entry point
cmd.append(str(ENTRY))

print(f"Building AccoBot v0.1.0 ...")
print(f"Command: {' '.join(cmd[:6])} ... ({len(cmd)} args)")
print()

result = subprocess.run(cmd, cwd=str(ROOT))
if result.returncode == 0:
    exe_path = ROOT / "dist" / "AccoBot.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ Build successful!")
        print(f"   Output: {exe_path}")
        print(f"   Size:   {size_mb:.1f} MB")
    else:
        print("\n✅ Build completed, check dist/ folder")
else:
    print(f"\n❌ Build failed with exit code {result.returncode}")
    sys.exit(1)
