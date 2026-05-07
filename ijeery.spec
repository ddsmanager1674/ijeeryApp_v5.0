# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for iJeery V5.0

block_cipher = None

a = Analysis(
    ['page_login.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('image', 'image'),
        ('icons', 'icons'),
        ('pages', 'pages'),
        ('config.json', '.'),
        ('config.ini', '.'),
    ],
    hiddenimports=[
        'customtkinter',
        'psycopg2',
        'psycopg2.extensions',
        'reportlab',
        'reportlab.lib',
        'reportlab.lib.pagesizes',
        'reportlab.lib.styles',
        'reportlab.lib.units',
        'reportlab.pdfgen',
        'reportlab.pdfgen.canvas',
        'reportlab.platypus',
        'PIL',
        'PIL.Image',
        'openpyxl',
        'num2words',
        'fpdf2',
        'pandas',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    icon='icons\\iconeIjeery.ico',
)
