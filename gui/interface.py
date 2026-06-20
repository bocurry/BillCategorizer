"""
interface.py - GUIInterface 主类，组合各 Mixin
"""

import queue
import threading
import tkinter as tk
from tkinter import ttk

from gui.classified_list import ClassifiedListMixin
from gui.dialogs import DialogMixin
from gui.results_panel import ResultsPanelMixin
from gui.thread_bridge import ThreadBridgeMixin
from gui.transaction_panel import TransactionPanelMixin


class GUIInterface(
    ThreadBridgeMixin,
    DialogMixin,
    TransactionPanelMixin,
    ClassifiedListMixin,
    ResultsPanelMixin,
):
    """GUI界面管理器 - 实现与 UserInterface 相同的接口。"""

    def __init__(self, config_manager):
        self.config = config_manager

        try:
            self.root = tk.Tk()
            self.root.title("账单自动分类助手")
            # 主窗口仅作事件循环容器，不展示欢迎界面
            self.root.withdraw()
        except Exception as e:
            raise RuntimeError(f"GUI初始化失败: {e}")

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        self.style.configure('Heading.TLabel', font=('Arial', 12, 'bold'))
        self.style.configure('Info.TLabel', font=('Arial', 10))
        self.style.configure('Action.TButton', padding=10)

        self.user_choice = None
        self.choice_event = threading.Event()
        self.task_queue = queue.Queue()

        self.transaction_window = None
        self.progress_var = None
        self.progress_label = None

        self.classified_list = []
        self.classified_tree = None
        self.classified_data = []
        self.tree_item_to_index = {}
        self.current_processed_df = None
        self.categorizer = None
        self.result_window = None

        self.should_stop = False
        self._welcome_shown = False
        self._progress_interval = max(
            1, int(self.config.get('display.progress_interval', 10) or 10)
        )
        self._txn_title_label = None
        self._txn_detail_text = None
        self._classification_menu_signature = None
        self._deferred_classified = []

        self._classification_menu_initialized = False
        self._action_buttons_built = False
        self._suggestions_outer = None
        self._suggestions_btn_container = None
        self._suggestion_buttons = []
        self._base_outer = None
        self._base_scrollable_frame = None
        self._base_category_buttons = []
        self._suggestions_signature = None
        self._base_categories_signature = None

        self.merge_to_master = bool(self.config.get('master_spreadsheet.enabled', False))

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._process_queue()

    def display_welcome(self):
        """GUI 模式不显示欢迎界面（保留接口以兼容 CLI 检测）。"""
        self._welcome_shown = True

    def _on_closing(self):
        """处理主窗口关闭事件。"""
        self.should_stop = True
        self.choice_event.set()
        self._destroy_transaction_window()

        if self.result_window and self._widget_alive(self.result_window):
            try:
                self.result_window.destroy()
            except tk.TclError:
                pass

        self.root.destroy()

    def run(self):
        """运行 GUI 主循环。"""
        self._process_queue()
        self.root.mainloop()

    def should_merge_to_master(self) -> bool:
        return bool(self.merge_to_master)

    def set_merge_to_master(self, enabled: bool):
        self.merge_to_master = bool(enabled)

    def ask_merge_to_master(self) -> bool:
        from tkinter import messagebox
        return bool(
            self.run_on_main_thread(
                lambda: messagebox.askyesno(
                    '同步到总表',
                    '是否将本次分类结果追加到年度总表？',
                ),
                default_on_stop=False,
            )
        )

    def destroy(self):
        """销毁窗口。"""
        if self.root:
            self.root.destroy()
