# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\python\\AccoBot\\accobot_web.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\python\\AccoBot\\accobot\\web\\static', 'accobot/web/static'), ('D:\\python\\AccoBot\\accobot\\standards', 'accobot/standards'), ('D:\\python\\AccoBot\\accobot\\skills', 'accobot/skills')],
    hiddenimports=['uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'accobot.web.routes', 'accobot.web.routes.config', 'accobot.web.routes.files', 'accobot.web.routes.chat', 'accobot.web.routes.ledger', 'accobot.web.routes.mcp', 'accobot.web.routes.todos', 'accobot.db.manager', 'accobot.db.master', 'accobot.db.accounting', 'accobot.db.chat_history', 'accobot.db.standards', 'accobot.db.templates', 'accobot.tools.registry', 'accobot.mcp.client', 'accobot.skills.loader', 'accobot.proactive'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AccoBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
