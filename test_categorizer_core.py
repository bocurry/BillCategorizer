"""categorizer.py 核心逻辑单元测试（无 GUI/文件 I/O）"""
from unittest.mock import MagicMock

import pytest

from categorizer import BillCategorizer
from data_loader import DataLoader


class _ConfigStub:
    def get(self, key, default=None):
        return default


def _make_categorizer(merge_master=False, ui=None, master_enabled=False):
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        'master_spreadsheet.prompt_before_merge': True,
        'master_spreadsheet.enabled': master_enabled,
    }.get(key, default)
    data_loader = MagicMock()
    learning_engine = MagicMock()
    data_exporter = MagicMock()
    ui = ui or MagicMock()
    master_merger = MagicMock()
    master_merger.is_enabled.return_value = master_enabled

    cat = BillCategorizer(
        config, data_loader, learning_engine, ui, data_exporter,
        merge_master=merge_master,
    )
    cat.master_merger = master_merger
    return cat


def test_should_merge_cli_flag():
    cat = _make_categorizer(merge_master=True, master_enabled=False)
    assert cat._should_merge_to_master() is True


def test_should_merge_gui_checkbox():
    ui = MagicMock()
    ui.should_merge_to_master.return_value = True
    cat = _make_categorizer(merge_master=False, ui=ui, master_enabled=False)
    assert cat._should_merge_to_master() is True


def test_should_merge_config_default():
    cat = _make_categorizer(merge_master=False, master_enabled=True)
    assert cat._should_merge_to_master() is True


def test_detect_bill_source_from_filename():
    assert DataLoader.detect_bill_source_from_path('2026-04-支付宝账单.csv') == '支付宝'
    assert DataLoader.detect_bill_source_from_path('2026-04-微信账单.xlsx') == '微信'
    assert DataLoader.detect_bill_source_from_path('unknown.csv') is None


def test_resolve_bill_source_prefers_filename():
    loader = DataLoader(_ConfigStub())
    resolved = loader.resolve_bill_source('2026-04-支付宝账单.csv', '微信')
    assert resolved == '支付宝'
