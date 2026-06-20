"""Tests for app_paths (PyInstaller layout)."""

import os
from pathlib import Path

import pytest


def test_get_app_dir_is_project_root_in_dev():
    from app_paths import get_app_dir, get_bundle_dir

    root = Path(__file__).resolve().parent
    assert get_app_dir() == root
    assert get_bundle_dir() == root


def test_ensure_runtime_files_idempotent(tmp_path, monkeypatch):
    from app_paths import ensure_runtime_files, get_app_dir

    monkeypatch.setattr('app_paths.get_app_dir', lambda: tmp_path)
    monkeypatch.setattr('app_paths.get_bundle_dir', lambda: tmp_path)
    (tmp_path / 'config.json').write_text('{}', encoding='utf-8')

    ensure_runtime_files()
    assert (tmp_path / 'config.json').exists()
    (tmp_path / 'config.json').write_text('{"x":1}', encoding='utf-8')
    ensure_runtime_files()
    assert (tmp_path / 'config.json').read_text(encoding='utf-8') == '{"x":1}'
