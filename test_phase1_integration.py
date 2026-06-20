"""
Phase 1 集成测试：模拟「继续处理 → 第二单」完整 worker 路径，无需人工点击。
"""
import os
import sys
import threading
import time
from collections import defaultdict
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SKIP_GUI = (
    os.environ.get('CI') == 'true'
    or os.environ.get('GITHUB_ACTIONS') == 'true'
)

pytestmark = pytest.mark.skipif(SKIP_GUI, reason="跳过 CI/无显示环境的 GUI 测试")


class _MinimalConfig:
    def get(self, key, default=None):
        data = {
            'categories.bill_sources': ['微信', '支付宝'],
            'categories.people_options': ['杜雨秦', '袁程波'],
            'categories.base_categories': ['餐饮', '购物', '其他'],
            'display.preview_count': 5,
            'display.progress_interval': 10,
        }
        return data.get(key, default)

    def set(self, key, value):
        pass

    def save_custom_config(self):
        pass


def _make_gui():
    from gui_interface import GUIInterface

    holder = {}
    ready = threading.Event()

    def tk_main():
        holder['gui'] = GUIInterface(_MinimalConfig())
        ready.set()
        holder['gui'].run()

    thread = threading.Thread(target=tk_main, daemon=True)
    thread.start()
    assert ready.wait(timeout=5), "GUI 初始化超时"
    time.sleep(0.3)
    return holder['gui']


def _shutdown_gui(gui):
    gui.should_stop = True
    gui.choice_event.set()
    done = threading.Event()

    def destroy():
        try:
            gui.root.destroy()
        except Exception:
            pass
        finally:
            done.set()

    gui.task_queue.put(destroy)
    done.wait(timeout=3)
    time.sleep(0.1)


def _sample_row(merchant='测试商户', amount=10.0):
    return {
        '交易对方': merchant,
        '商品': '测试商品',
        '交易类型': '支出',
        '交易时间': '2026-04-01 12:00:00',
        '处理后的金额': -amount,
        '金额(元)': amount,
        '收/支': '支出',
    }


def test_worker_continue_then_second_bill_tree_operations():
    """
    回归：第一单结束后 _prepare_for_continue_dialog 销毁窗口，
    worker 线程继续第二单时不应访问已销毁的 treeview。
    """
    gui = _make_gui()
    errors = []

    def worker():
        try:
            row1 = _sample_row('商户A', 12.5)
            gui.run_on_main_thread(gui._create_transaction_window)
            gui.run_on_main_thread(
                gui.add_classified_transaction, row1, '餐饮', '杜雨秦', True
            )
            assert gui.run_on_main_thread(lambda: gui._widget_alive(gui.classified_tree))

            # 模拟 ask_continue_processing 开头
            gui.run_on_main_thread(gui._prepare_for_continue_dialog)
            assert gui.run_on_main_thread(lambda: gui.classified_tree is None)

            # 模拟 categorizer 第二单循环：_reset_gui_for_next_bill
            from categorizer import BillCategorizer

            cat = BillCategorizer(
                config_manager=_MinimalConfig(),
                data_loader=MagicMock(),
                learning_engine=MagicMock(),
                user_interface=gui,
                data_exporter=MagicMock(),
            )
            cat._reset_gui_for_next_bill()

            # 模拟 _process_transactions 开头清空
            import pandas as pd

            df = pd.DataFrame([row1, _sample_row('商户B', 8.0)])
            cat._process_transactions(df.iloc[:1], 'fixed')  # 只处理 1 条后 break 模拟

            # 第二单：重建窗口并写入 tree
            gui.run_on_main_thread(gui._create_transaction_window)
            row2 = _sample_row('商户B', 8.0)
            gui.run_on_main_thread(
                gui.add_classified_transaction, row2, '购物', '杜雨秦', False
            )
            alive = gui.run_on_main_thread(lambda: gui._widget_alive(gui.classified_tree))
            if not alive:
                raise AssertionError('第二单 classified_tree 未成功创建')
        except Exception as exc:
            errors.append(exc)

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=15)
    try:
        assert not errors, errors
    finally:
        _shutdown_gui(gui)


def test_ask_continue_processing_prepare_and_reset_from_worker():
    """ask_continue 前的 destroy + 后续 reset 在 worker 线程完整走通。"""
    gui = _make_gui()
    errors = []

    def worker():
        try:
            gui.run_on_main_thread(gui._create_transaction_window)
            gui.run_on_main_thread(
                gui.add_classified_transaction,
                _sample_row(),
                '餐饮',
                '杜雨秦',
                True,
            )
            gui.run_on_main_thread(gui._prepare_for_continue_dialog)
            assert gui.run_on_main_thread(lambda: gui.classified_tree is None)

            from categorizer import BillCategorizer

            cat = BillCategorizer(
                _MinimalConfig(), MagicMock(), MagicMock(), gui, MagicMock()
            )
            cat._reset_gui_for_next_bill()
            gui.run_on_main_thread(gui.reset_bill_processing_state)
            gui.run_on_main_thread(gui._create_transaction_window)
            gui.run_on_main_thread(
                gui.add_classified_transaction,
                _sample_row('商户C'),
                '购物',
                '杜雨秦',
                False,
            )
        except Exception as exc:
            errors.append(exc)

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=15)
    try:
        assert not errors, errors
    finally:
        _shutdown_gui(gui)


def test_cli_mode_has_show_error_and_no_gui_bridge_required():
    """CLI 模式不依赖 GUI 桥接即可报错。"""
    from user_interface import UserInterface

    ui = UserInterface(_MinimalConfig())
    assert not hasattr(ui, 'run_on_main_thread')
    ui.show_error('读取文件失败')
    ui.show_info('提示')
