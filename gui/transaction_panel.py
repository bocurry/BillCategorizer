"""
transaction_panel.py - 交易窗口、分类菜单与已分类列表
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox


class TransactionPanelMixin:
    """交易处理面板、分类菜单与已分类 Treeview。"""

    def _invalidate_transaction_widgets(self):
        """交易窗口销毁后清空子控件引用，避免 invalid command name。"""
        self.classified_tree = None
        self.transaction_info_frame = None
        self.classification_frame = None
        self.button_frame = None
        self.progress_var = None
        self.progress_label = None
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

    def _should_update_progress(self, current: int, total: int) -> bool:
        """按 progress_interval 节流进度条刷新。"""
        if total <= 0:
            return False
        if current >= total:
            return True
        return current % self._progress_interval == 0

    def flush_deferred_classified_transactions(self):
        """刷新批量暂存的自动分类 Treeview 条目（主线程）。"""
        if not self._deferred_classified:
            return
        batch = self._deferred_classified[:]
        self._deferred_classified.clear()
        for row, category, person, is_auto in batch:
            self.add_classified_transaction(row, category, person, is_auto)

    def defer_classified_transaction(
        self, row: dict, category: str, person: str, is_auto: bool, current: int, total: int
    ):
        """自动分类时批量追加 Treeview，减少主线程调度次数。"""
        self._deferred_classified.append((row, category, person, is_auto))
        if self._should_update_progress(current, total):
            self.flush_deferred_classified_transactions()

    def _destroy_transaction_window(self, release_grab: bool = False):
        """销毁交易窗口并清理全部相关引用。"""
        if self.transaction_window:
            try:
                if self._widget_alive(self.transaction_window):
                    if release_grab:
                        try:
                            self.transaction_window.grab_release()
                        except tk.TclError:
                            pass
                    self.transaction_window.destroy()
            except tk.TclError:
                pass
        self.transaction_window = None
        self._invalidate_transaction_widgets()

    def reset_bill_processing_state(self):
        """重置单笔账单 GUI 状态（须在主线程调用）。"""
        self.classified_data = []
        self.tree_item_to_index = {}
        self.current_processed_df = None
        self._deferred_classified = []
        self._classification_menu_signature = None
        self._suggestions_signature = None
        if self._widget_alive(self.classified_tree):
            for item in self.classified_tree.get_children():
                self.classified_tree.delete(item)

    def _on_transaction_window_closing(self):
        """处理交易窗口关闭事件。"""
        self.should_stop = True
        self.choice_event.set()
        self._destroy_transaction_window()

    def display_transaction(self, idx: int, total: int, row: dict):
        """显示交易信息。"""
        if threading.current_thread() is not threading.main_thread():
            return self.run_on_main_thread(
                self._display_transaction_impl, idx, total, row
            )
        return self._display_transaction_impl(idx, total, row)

    def _display_transaction_impl(self, idx: int, total: int, row: dict):
        """在主线程更新交易信息面板。"""
        # 显示第 N 笔前，先把暂存的自动分类写入 Treeview（避免右侧列表落后进度）
        if idx > 1:
            self.flush_deferred_classified_transactions()

        if not self._widget_alive(self.transaction_window):
            self._create_transaction_window()

        merchant = str(row.get('交易对方', '未知商户'))
        product = str(row.get('商品', '无'))
        amount = row.get('处理后的金额', row.get('金额(元)', 0))
        date = row.get('交易时间', '未知时间')

        if not self._widget_alive(getattr(self, '_txn_title_label', None)):
            self._txn_title_label = ttk.Label(
                self.transaction_info_frame,
                text='',
                style='Title.TLabel',
            )
            self._txn_title_label.pack(pady=5, anchor=tk.W)
            self._txn_detail_text = tk.Text(
                self.transaction_info_frame,
                height=5,
                wrap=tk.WORD,
                font=('Arial', 10),
                relief=tk.FLAT,
                borderwidth=0,
            )
            self._txn_detail_text.pack(fill=tk.X, pady=5)

        self._txn_title_label.config(text=f"交易 {idx}/{total}")
        info_lines = [
            f"时间: {date}",
            f"商户: {merchant}",
            f"商品: {product}",
        ]
        if isinstance(amount, (int, float)):
            info_lines.append(f"金额: ¥{amount:+.2f}")
        else:
            info_lines.append(f"金额: {amount}")
        info_text = "\n".join(info_lines)
        self._txn_detail_text.config(state=tk.NORMAL)
        self._txn_detail_text.delete('1.0', tk.END)
        self._txn_detail_text.insert('1.0', info_text)
        self._txn_detail_text.config(state=tk.DISABLED)

        # 进度条与「交易 idx/total」保持同步，不做 interval 节流
        if self.progress_var:
            progress = (idx / total * 100) if total > 0 else 0
            self.progress_var.set(progress)
        if self.progress_label:
            progress = (idx / total * 100) if total > 0 else 0
            self.progress_label.config(text=f"进度: {idx}/{total} ({progress:.1f}%)")

    def _create_transaction_window(self):
        """创建交易处理窗口。"""
        self.transaction_window = tk.Toplevel(self.root)
        self.transaction_window.title("处理交易")
        self.transaction_window.geometry("700x600")

        self.transaction_window.update_idletasks()
        x = (self.transaction_window.winfo_screenwidth() // 2) - (1000 // 2)
        y = (self.transaction_window.winfo_screenheight() // 2) - (700 // 2)
        self.transaction_window.geometry(f"1000x700+{x}+{y}")

        self.transaction_window.protocol("WM_DELETE_WINDOW", self._on_transaction_window_closing)
        self._attach_toplevel(self.transaction_window)

        progress_frame = ttk.Frame(self.transaction_window, padding="10")
        progress_frame.pack(fill=tk.X, pady=5)

        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=400
        )
        progress_bar.pack(side=tk.LEFT, padx=5)

        self.progress_label = ttk.Label(progress_frame, text="进度: 0/0 (0%)")
        self.progress_label.pack(side=tk.LEFT, padx=5)

        info_frame = ttk.LabelFrame(self.transaction_window, text="当前交易信息", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        self.transaction_info_frame = ttk.Frame(info_frame)
        self.transaction_info_frame.pack(fill=tk.BOTH, expand=True)

        main_container = ttk.Frame(self.transaction_window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        left_frame = ttk.Frame(main_container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.classification_frame = ttk.LabelFrame(left_frame, text="分类选择", padding="10")
        self.classification_frame.pack(fill=tk.BOTH, expand=True)

        right_frame = ttk.Frame(main_container)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        classified_frame = ttk.LabelFrame(right_frame, text="已分类账单", padding="10")
        classified_frame.pack(fill=tk.BOTH, expand=True)

        classified_tree_frame = ttk.Frame(classified_frame)
        classified_tree_frame.pack(fill=tk.BOTH, expand=True)

        classified_scrollbar_y = ttk.Scrollbar(classified_tree_frame, orient=tk.VERTICAL)
        classified_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        classified_scrollbar_x = ttk.Scrollbar(classified_tree_frame, orient=tk.HORIZONTAL)
        classified_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.classified_tree = ttk.Treeview(
            classified_tree_frame,
            columns=('时间', '商户', '商品', '金额', '分类', '人员', '是否自动分类'),
            show='headings',
            yscrollcommand=classified_scrollbar_y.set,
            xscrollcommand=classified_scrollbar_x.set,
            height=15
        )

        for col, width in (
            ('时间', 120), ('商户', 150), ('商品', 150), ('金额', 80),
            ('分类', 100), ('人员', 80), ('是否自动分类', 100),
        ):
            self.classified_tree.heading(col, text=col)
            self.classified_tree.column(col, width=width)

        self.classified_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        classified_scrollbar_y.config(command=self.classified_tree.yview)
        classified_scrollbar_x.config(command=self.classified_tree.xview)

        self.classified_tree.bind('<Double-Button-1>', self._on_classified_item_double_click)
        self.classified_tree.bind('<Button-3>', self._on_classified_item_right_click)

        self.button_frame = ttk.Frame(self.transaction_window, padding="10")
        self.button_frame.pack(fill=tk.X, pady=5)

    def display_classification_menu(self, suggestions: dict, base_categories: list):
        """显示分类选择菜单。"""
        if threading.current_thread() is not threading.main_thread():
            return self.run_on_main_thread(
                self._display_classification_menu_impl, suggestions, base_categories
            )
        return self._display_classification_menu_impl(suggestions, base_categories)

    def _classification_signature(self, suggestions: dict, base_categories: list):
        return (tuple(suggestions.items()), tuple(base_categories))

    def _ensure_action_buttons(self):
        """操作按钮 (n/s/q) 仅构建一次。"""
        if self._action_buttons_built or not self._widget_alive(self.button_frame):
            return
        for widget in self.button_frame.winfo_children():
            widget.destroy()
        ttk.Button(
            self.button_frame,
            text="输入新分类 (n)",
            command=lambda: self._set_category_choice('n')
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            self.button_frame,
            text="跳过 (s)",
            command=lambda: self._set_category_choice('s')
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            self.button_frame,
            text="退出 (q)",
            command=lambda: self._set_category_choice('q')
        ).pack(side=tk.LEFT, padx=5)
        self._action_buttons_built = True

    def _ensure_classification_menu_shell(self, base_categories: list):
        """首次构建分类菜单静态结构（基础分类 Canvas 与操作按钮）。"""
        if self._classification_menu_initialized:
            return

        for widget in self.classification_frame.winfo_children():
            widget.destroy()

        self._suggestions_outer = ttk.Frame(self.classification_frame)
        self._suggestions_outer.pack(fill=tk.X, pady=5)
        ttk.Label(
            self._suggestions_outer,
            text="系统建议:",
            style='Heading.TLabel'
        ).pack(anchor=tk.W)
        self._suggestions_btn_container = ttk.Frame(self._suggestions_outer)
        self._suggestions_btn_container.pack(fill=tk.X)
        self._suggestion_buttons = []

        self._base_outer = ttk.Frame(self.classification_frame)
        self._base_outer.pack(fill=tk.BOTH, expand=True, pady=5)
        ttk.Label(
            self._base_outer,
            text="基础分类:",
            style='Heading.TLabel'
        ).pack(anchor=tk.W)

        canvas = tk.Canvas(self._base_outer, height=250)
        scrollbar = ttk.Scrollbar(self._base_outer, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._base_scrollable_frame = scrollable_frame
        self._base_category_buttons = []
        self._build_base_category_buttons(base_categories)
        self._base_categories_signature = tuple(base_categories)

        self._ensure_action_buttons()
        self._classification_menu_initialized = True

    def _build_base_category_buttons(self, base_categories: list):
        """在可滚动区域内构建基础分类按钮（仅 base_categories 变化时重建）。"""
        for btn in self._base_category_buttons:
            btn.destroy()
        self._base_category_buttons = []

        scrollable_frame = self._base_scrollable_frame
        for i, category in enumerate(base_categories):
            row, col = i // 2, i % 2
            btn = ttk.Button(scrollable_frame, text='', width=30)
            btn.grid(row=row, column=col, sticky=tk.W + tk.E, padx=10, pady=2)
            btn._base_category = category  # pylint: disable=protected-access
            self._base_category_buttons.append(btn)

        scrollable_frame.columnconfigure(0, weight=1)
        scrollable_frame.columnconfigure(1, weight=1)

    def _update_suggestions_buttons(self, suggestions: dict):
        """增量更新建议区按钮（show/hide + rebind，不 destroy 整区）。"""
        suggestions_list = list(suggestions.items())
        needed = len(suggestions_list)

        if needed == 0:
            self._suggestions_outer.pack_forget()
        elif not self._suggestions_outer.winfo_manager():
            self._suggestions_outer.pack(fill=tk.X, pady=5, before=self._base_outer)
        else:
            self._suggestions_outer.pack(fill=tk.X, pady=5, before=self._base_outer)

        while len(self._suggestion_buttons) < needed:
            btn = ttk.Button(self._suggestions_btn_container, width=50)
            self._suggestion_buttons.append(btn)

        for i, btn in enumerate(self._suggestion_buttons):
            if i < needed:
                category, reason = suggestions_list[i]
                idx = i + 1
                btn.config(
                    text=f"[{idx}] {category} ← {reason}",
                    command=lambda idx=idx: self._set_category_choice(idx),
                )
                btn.pack(anchor=tk.W, pady=2, padx=20)
            else:
                btn.pack_forget()

    def _rebind_base_category_indices(self, suggestions_count: int, base_categories: list):
        """suggestions 数量变化时重绑基础分类按钮 idx（与 category_choice 一致）。"""
        start_idx = suggestions_count + 1
        for i, btn in enumerate(self._base_category_buttons):
            if i >= len(base_categories):
                break
            category = base_categories[i]
            idx = start_idx + i
            btn.config(
                text=f"[{idx}] {category}",
                command=lambda idx=idx: self._set_category_choice(idx),
            )

    def _display_classification_menu_impl(self, suggestions: dict, base_categories: list):
        """在主线程显示分类选择菜单（建议区增量更新，基础分类 Canvas 复用）。"""
        if not self._widget_alive(self.transaction_window):
            self._create_transaction_window()

        if not self._widget_alive(getattr(self, 'classification_frame', None)):
            return

        suggestions_sig = tuple(suggestions.items())
        base_sig = tuple(base_categories)
        suggestions_changed = suggestions_sig != self._suggestions_signature
        base_changed = base_sig != self._base_categories_signature

        if (
            self._classification_menu_initialized
            and not suggestions_changed
            and not base_changed
        ):
            return

        prev_suggestions_count = (
            len(self._suggestions_signature) if self._suggestions_signature is not None else None
        )

        self._ensure_classification_menu_shell(base_categories)

        if base_changed:
            self._build_base_category_buttons(base_categories)
            self._base_categories_signature = base_sig

        if suggestions_changed:
            self._update_suggestions_buttons(suggestions)
            self._suggestions_signature = suggestions_sig

        if base_changed or suggestions_changed or prev_suggestions_count != len(suggestions):
            self._rebind_base_category_indices(len(suggestions), base_categories)

        self._classification_menu_signature = (suggestions_sig, base_sig)

    def _set_category_choice(self, choice):
        """设置分类选择。"""
        self.user_choice = choice
        self.choice_event.set()

    def add_classified_transaction(self, row: dict, category: str, person: str, is_auto: bool = False):
        """添加已分类的交易到列表中。"""
        if not self._widget_alive(self.classified_tree):
            return

        date = str(row.get('交易时间', '未知时间'))
        if len(date) > 19:
            date = date[:19]

        merchant = str(row.get('交易对方', '未知商户'))
        product = str(row.get('商品', '无'))
        amount = row.get('处理后的金额', row.get('金额(元)', 0))

        if isinstance(amount, (int, float)):
            amount_str = f"¥{amount:+.2f}"
        else:
            amount_str = str(amount)

        is_auto_str = '是' if is_auto else '否'

        item_id = self.classified_tree.insert(
            '',
            0,
            values=(date, merchant, product, amount_str, category, person, is_auto_str)
        )

        data_entry = {
            'row': row.copy(),
            'category': category,
            'person': person,
            'is_auto': is_auto,
            'tree_item_id': item_id,
        }
        self.classified_data.insert(0, data_entry)

        for existing_id, pos in self.tree_item_to_index.items():
            self.tree_item_to_index[existing_id] = pos + 1
        self.tree_item_to_index[item_id] = 0
        data_entry['index'] = len(self.classified_data) - 1

        if len(self.classified_data) % self._progress_interval == 0:
            children = self.classified_tree.get_children()
            if children:
                self.classified_tree.see(children[0])

    def display_progress(self, current: int, total: int):
        """显示处理进度。"""
        if threading.current_thread() is not threading.main_thread():
            return self.run_on_main_thread(self._display_progress_impl, current, total)
        return self._display_progress_impl(current, total)

    def _display_progress_impl(self, current: int, total: int):
        """在主线程更新进度条。"""
        if not self._should_update_progress(current, total):
            return
        if self.progress_var and self.progress_label:
            progress = (current / total * 100) if total > 0 else 0
            self.progress_var.set(progress)
            self.progress_label.config(text=f"进度: {current}/{total} ({progress:.1f}%)")
