"""
app_paths.py - 开发环境与 PyInstaller 打包后的路径解析

- get_bundle_dir(): 只读捆绑资源（开发时为项目根目录）
- get_app_dir(): 可写应用目录（打包后为 exe 所在文件夹）
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_BUNDLE_DATA_FILES = (
    'config.json',
    'bill_rules_optimized.json',
    'bill_history.json',
)


def is_frozen() -> bool:
    return bool(getattr(sys, 'frozen', False))


def get_bundle_dir() -> Path:
    if is_frozen():
        return Path(getattr(sys, '_MEIPASS'))
    return Path(__file__).resolve().parent


def get_app_dir() -> Path:
    """可写目录：打包后为 BillCategorizer.exe 所在文件夹。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def ensure_runtime_files() -> Path:
    """首次运行时把捆绑的 JSON 复制到 exe 目录（可写）。"""
    app_dir = get_app_dir()
    bundle_dir = get_bundle_dir()
    for name in _BUNDLE_DATA_FILES:
        target = app_dir / name
        source = bundle_dir / name
        if not target.exists() and source.is_file():
            shutil.copy2(source, target)
    return app_dir


def set_working_directory() -> Path:
    """将进程 cwd 设为 exe 目录，便于查找账单与导出 CSV。"""
    app_dir = ensure_runtime_files()
    os.chdir(app_dir)
    return app_dir
