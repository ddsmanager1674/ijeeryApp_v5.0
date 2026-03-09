# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['customtkinter', 'psycopg2', 'reportlab', 'PIL', 'openpyxl', 'pandas']
hiddenimports += collect_submodules('pages')


a = Analysis(
    ['page_login.py'],
    pathex=[],
    binaries=[],
    datas=[('image', 'image'), ('icons', 'icons'), ('pages', 'pages'), ('config.json', '.'), ('config.ini', '.'), ('settings.json', '.'), ('session.json', '.')],
    hiddenimports=hiddenimports,
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
    name='iJeery_V5.0',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='iJeery_V5.0',
)
