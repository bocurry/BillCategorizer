"""
GUI 线程安全与多账单流程测试
"""
import os
import sys
import threading
import time

import pytest

# 确保项目根目录在 path 中
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
    """在专用 Tk 线程创建 GUI 并启动 mainloop（与生产环境主线程模型一致）。"""
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
    """安全关闭测试用 GUI。"""
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


def test_run_on_main_thread_bridge():
    """worker 线程可经 run_on_main_thread 在主线程执行 tk 调用。"""
    gui = _make_gui()
    try:
        result = {}
        errors = []

        def worker():
            try:
                result['exists'] = gui.run_on_main_thread(gui.root.winfo_exists)
                result['thread_ok'] = threading.current_thread() is not threading.main_thread()
            except Exception as exc:
                errors.append(exc)

        t = threading.Thread(target=worker)
        t.start()
        t.join(timeout=5)
        assert not errors, errors
        assert result.get('exists')
        assert result.get('thread_ok') is True
    finally:
        _shutdown_gui(gui)


def test_run_on_main_thread_should_stop():
    """should_stop=True 时 run_on_main_thread 返回哨兵值。"""
    gui = _make_gui()
    try:
        gui.should_stop = True
        sentinel = object()
        holder = {}

        def worker():
            holder['out'] = gui.run_on_main_thread(
                lambda: 1 / 0, default_on_stop=sentinel
            )

        t = threading.Thread(target=worker)
        t.start()
        t.join(timeout=5)
        assert holder.get('out') is sentinel
    finally:
        _shutdown_gui(gui)


def test_modal_dialog_from_worker_thread():
    """worker 线程调用模态路径不抛 tkinter 线程错误。"""
    gui = _make_gui()
    try:
        choice_holder = {}

        def worker():
            def mini_dialog():
                dlg = __import__('tkinter').Toplevel(gui.root)
                dlg.withdraw()
                gui._set_choice_and_close('微信', dlg)

            choice_holder['result'] = gui._show_modal_dialog(mini_dialog)

        t = threading.Thread(target=worker)
        t.start()
        t.join(timeout=5)
        assert choice_holder.get('result') == '微信'
    finally:
        _shutdown_gui(gui)


def test_ask_continue_lifecycle():
    """_prepare_for_continue_dialog 会销毁 transaction_window 并清空 tree 引用。"""
    import tkinter as tk
    from tkinter import ttk

    gui = _make_gui()
    try:
        gui.transaction_window = tk.Toplevel(gui.root)
        gui.classified_tree = ttk.Treeview(gui.transaction_window)
        gui._prepare_for_continue_dialog()
        assert gui.transaction_window is None
        assert gui.classified_tree is None
    finally:
        _shutdown_gui(gui)


def test_reset_bill_processing_after_destroyed_tree():
    """销毁交易窗口后 reset_bill_processing_state 不应抛 TclError。"""
    gui = _make_gui()
    try:
        gui._destroy_transaction_window()
        gui.classified_data = [{'tree_item_id': 'x'}]
        gui.reset_bill_processing_state()
        assert gui.classified_data == []
        assert gui.classified_tree is None
    finally:
        _shutdown_gui(gui)


def test_multi_bill_continue_flow_smoke():
    """连续两轮 ask_continue 预设选择不抛异常。"""
    gui = _make_gui()
    try:
        results = []

        def run_flow():
            gui.user_choice = True
            gui.choice_event.set()

            def fake_continue():
                dlg = __import__('tkinter').Toplevel(gui.root)
                dlg.withdraw()
                gui._set_choice_and_close(True, dlg)

            gui._prepare_for_continue_dialog()
            results.append(gui._show_modal_dialog(fake_continue))
            gui._prepare_for_continue_dialog()
            results.append(gui._show_modal_dialog(fake_continue))

        gui.run_on_main_thread(run_flow)
        assert results == [True, True]
    finally:
        _shutdown_gui(gui)


def test_transaction_panel_reuses_widgets():
    """连续更新交易面板时不累积 destroy/create 子控件。"""
    gui = _make_gui()
    try:
        row = {
            '交易对方': '商户A',
            '商品': '商品A',
            '交易时间': '2026-04-01',
            '处理后的金额': -10.0,
        }

        def run_updates():
            gui._display_transaction_impl(1, 3, row)
            count_after_first = len(gui.transaction_info_frame.winfo_children())
            gui._display_transaction_impl(2, 3, row)
            count_after_second = len(gui.transaction_info_frame.winfo_children())
            return count_after_first, count_after_second

        c1, c2 = gui.run_on_main_thread(run_updates)
        assert c1 == c2 == 2  # title + text
    finally:
        _shutdown_gui(gui)


def test_classified_tree_incremental_index():
    """add_classified_transaction 增量维护 df index。"""
    gui = _make_gui()
    try:
        row = {'交易时间': '2026-04-01', '交易对方': 'M', '商品': 'P', '处理后的金额': 1}

        def add_three():
            gui._create_transaction_window()
            for i in range(3):
                gui.add_classified_transaction(row, f'类{i}', '人', True)

        gui.run_on_main_thread(add_three)
        indices = [e['index'] for e in gui.classified_data]
        assert indices == [2, 1, 0]
        assert gui.tree_item_to_index == {e['tree_item_id']: i for i, e in enumerate(gui.classified_data)}
    finally:
        _shutdown_gui(gui)


def test_progress_syncs_with_transaction_display():
    """显示交易时进度条应与 idx/total 同步，不受 progress_interval 节流。"""
    gui = _make_gui()
    try:
        gui._progress_interval = 10
        gui._create_transaction_window()
        row = {'交易时间': '2024-01-01', '交易对方': '商户', '商品': 'x', '处理后的金额': 1.0}
        gui._display_transaction_impl(6, 49, row)
        assert gui.progress_label.cget('text') == '进度: 6/49 (12.2%)'
        assert gui.progress_var.get() == pytest.approx(6 / 49 * 100)
    finally:
        _shutdown_gui(gui)


def test_progress_throttling():
    """progress_interval 节流生效。"""
    gui = _make_gui()
    try:
        gui._progress_interval = 10
        assert gui._should_update_progress(5, 100) is False
        assert gui._should_update_progress(10, 100) is True
        assert gui._should_update_progress(100, 100) is True
    finally:
        _shutdown_gui(gui)


def test_gui_interface_has_unified_person_dialog():
    """Wave 2 回归：GUIInterface 必须暴露 _select_unified_person。"""
    gui = _make_gui()
    try:
        assert hasattr(gui, '_select_unified_person')
        assert callable(gui._select_unified_person)
    finally:
        _shutdown_gui(gui)


def test_deferred_classified_flushed_before_next_transaction_display():
    """自动分类 defer 后，显示下一笔交易前应刷新已分类列表。"""
    gui = _make_gui()
    try:
        gui._create_transaction_window()
        row = {'交易时间': '2024-01-01', '交易对方': '商户', '商品': 'x', '处理后的金额': 1.0}
        for i in range(1, 6):
            gui.defer_classified_transaction(row, f'类{i}', '人', True, i, 49)
        assert len(gui.classified_data) == 0
        gui._display_transaction_impl(6, 49, row)
        assert len(gui.classified_data) == 5
    finally:
        _shutdown_gui(gui)


def test_cli_ui_has_no_run_on_main_thread_requirement():
    """CLI UserInterface 不依赖 run_on_main_thread。"""
    from user_interface import UserInterface

    ui = UserInterface(_MinimalConfig())
    assert not hasattr(ui, 'run_on_main_thread')
    ui.show_error("test")
    ui.show_info("test")


@pytest.mark.skipif(SKIP_GUI, reason="跳过CI环境中的GUI测试")
def test_gui_interactive():
    """交互式 GUI 冒烟（本地手动）。"""
    import tkinter as tk
    from tkinter import ttk, messagebox

    root = tk.Tk()
    root.title("GUI测试")
    root.geometry("400x300")
    root.deiconify()
    label = ttk.Label(root, text="如果看到这个窗口，说明GUI正常工作！", font=("Arial", 12))
    label.pack(pady=50)

    def show_message():
        messagebox.showinfo("测试", "消息框测试成功！")

    btn = ttk.Button(root, text="测试消息框", command=show_message)
    btn.pack(pady=20)
    root.after(2000, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
