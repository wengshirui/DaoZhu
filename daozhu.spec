# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\python\\Daozhu\\daozhu_main.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\python\\Daozhu\\daozhu\\frontend', 'daozhu/frontend'), ('D:\\python\\Daozhu\\templates', 'templates'), ('D:\\python\\Daozhu\\skills', 'skills'), ('D:\\python\\Daozhu\\workspaces', 'workspaces')],
    hiddenimports=['uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on'],
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
    [],
    exclude_binaries=True,
    name='daozhu',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:\\python\\Daozhu\\daozhu\\frontend\\favicon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='daozhu',
)
