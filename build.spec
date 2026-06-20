# build.spec — PyInstaller 打包（onedir，输出 dist/BillCategorizer/BillCategorizer.exe）
# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

block_cipher = None
project_dir = Path(SPECPATH)

datas = [
    (str(project_dir / 'config.json'), '.'),
    (str(project_dir / 'bill_rules_optimized.json'), '.'),
    (str(project_dir / 'bill_history.json'), '.'),
]

hiddenimports = [
    'pandas',
    'openpyxl',
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'app_paths',
    'gui',
    'gui.interface',
    'gui.thread_bridge',
    'gui.dialogs',
    'gui.transaction_panel',
    'gui.classified_list',
    'gui.results_panel',
    'gui_interface',
]

a = Analysis(
    [str(project_dir / 'main.py')],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(project_dir / 'hooks' / 'pyi_rth_billcategorizer.py')],
    excludes=[],
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
    name='BillCategorizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='BillCategorizer',
)
