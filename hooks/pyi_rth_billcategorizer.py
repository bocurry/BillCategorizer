"""PyInstaller runtime hook: 打包启动时尽早固定工作目录。"""
import sys

if getattr(sys, 'frozen', False):
    try:
        from app_paths import set_working_directory
        set_working_directory()
    except Exception:
        pass
