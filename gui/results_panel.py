"""
results_panel.py - 处理结果预览与统计
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox


class ResultsPanelMixin:
    """结果窗口与数据预览。"""

    def show_results(self, final_df, output_file, stats, engine_stats, merge_result=None):
        """显示处理结果，并在同一窗口收集「继续 / 退出」选择。"""
        if threading.current_thread() is not threading.main_thread():
            return self.run_on_main_thread(
                self.show_results, final_df, output_file, stats, engine_stats, merge_result
            )
        return self._show_results_impl(final_df, output_file, stats, engine_stats, merge_result)

    def _sync_current_bill_to_master(self, final_df, status_label=None):
        """将当前账单追加到年度总表。"""
        from master_spreadsheet import MasterSpreadsheetMerger

        merger = MasterSpreadsheetMerger(self.config)
        result = merger.merge_dataframe(final_df)
        if result.success:
            msg = result.summary()
            if status_label is not None:
                status_label.config(text=f'总表合并：{msg}')
            messagebox.showinfo('同步成功', msg)
        else:
            messagebox.showerror('同步失败', result.error, parent=self.result_window)
        return result

    def _show_results_impl(self, final_df, output_file, stats, engine_stats, merge_result=None):
        """在主线程显示处理结果，并等待用户选择是否继续。"""
        self._last_export_df = final_df
        self._result_continue_choice = None

        if self.result_window and self.result_window.winfo_exists():
            self.result_window.destroy()

        self.result_window = tk.Toplevel(self.root)
        self.result_window.title("处理结果")
        self.result_window.geometry("900x700")

        self.result_window.update_idletasks()
        x = (self.result_window.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.result_window.winfo_screenheight() // 2) - (700 // 2)
        self.result_window.geometry(f"900x700+{x}+{y}")

        self.result_window.protocol("WM_DELETE_WINDOW", self.result_window.destroy)

        notebook = ttk.Notebook(self.result_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        preview_frame = ttk.Frame(notebook, padding="10")
        notebook.add(preview_frame, text="数据预览")

        tree_frame = ttk.Frame(preview_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar_y = ttk.Scrollbar(tree_frame)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        tree = ttk.Treeview(
            tree_frame,
            columns=('Name', 'Category', 'Amount', 'Date', 'Person', 'Source', '是否自动分类'),
            show='headings',
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        tree.heading('Name', text='名称')
        tree.heading('Category', text='分类')
        tree.heading('Amount', text='金额')
        tree.heading('Date', text='日期')
        tree.heading('Person', text='人员')
        tree.heading('Source', text='来源')
        tree.heading('是否自动分类', text='是否自动分类')

        tree.column('Name', width=200)
        tree.column('Category', width=100)
        tree.column('Amount', width=100)
        tree.column('Date', width=100)
        tree.column('Person', width=100)
        tree.column('Source', width=80)
        tree.column('是否自动分类', width=100)

        scrollbar_y.config(command=tree.yview)
        scrollbar_x.config(command=tree.xview)

        preview_count = min(100, len(final_df))
        for i in range(preview_count):
            row = final_df.iloc[i]
            tree.insert('', tk.END, values=(
                str(row.get('Name', ''))[:50],
                str(row.get('Category', '')),
                f"¥{row.get('Amount', 0):+.2f}",
                str(row.get('Date', '')),
                str(row.get('Person', '')),
                str(row.get('Source', '')),
                str(row.get('是否自动分类', '否'))
            ))

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.result_preview_tree = tree

        stats_frame = ttk.Frame(notebook, padding="10")
        notebook.add(stats_frame, text="统计信息")

        stats_text = f"""
处理统计
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总记录数: {stats.get('total', 0)}
自动分类: {stats.get('auto', 0)}
手动分类: {stats.get('manual', 0)}
跳过记录: {stats.get('skipped', 0)}

规则库状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
当前规则数: {engine_stats.get('total_rules', 0)} / {engine_stats.get('max_rules', 0)}
历史记录数: {engine_stats.get('total_history', 0)} / {engine_stats.get('max_history', 0)}

导出文件
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{output_file}
        """

        if merge_result is not None:
            stats_text += f"""

总表合并
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{merge_result.summary()}
            """

        stats_label = ttk.Label(
            stats_frame,
            text=stats_text.strip(),
            font=("Arial", 10),
            justify=tk.LEFT
        )
        stats_label.pack(anchor=tk.W, pady=10)

        btn_frame = ttk.Frame(self.result_window, padding="10")
        btn_frame.pack(fill=tk.X)

        merge_var = tk.BooleanVar(value=self.merge_to_master)
        merge_status = ttk.Label(btn_frame, text='', style='Info.TLabel')

        def _on_merge_toggle():
            self.set_merge_to_master(merge_var.get())

        ttk.Checkbutton(
            btn_frame,
            text='后续账单自动同步到总表',
            variable=merge_var,
            command=_on_merge_toggle,
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            btn_frame,
            text='同步本单到总表',
            command=lambda: self._sync_current_bill_to_master(final_df, merge_status),
        ).pack(side=tk.LEFT, padx=(0, 10))

        merge_status.pack(side=tk.LEFT, padx=(0, 10))

        action_frame = ttk.Frame(self.result_window, padding="10")
        action_frame.pack(fill=tk.X)

        def _finish(should_continue: bool):
            self._result_continue_choice = should_continue
            self.result_window.destroy()

        ttk.Button(
            action_frame,
            text='是，继续处理',
            command=lambda: _finish(True),
            width=16,
        ).pack(side=tk.LEFT, padx=10)

        ttk.Button(
            action_frame,
            text='否，退出程序',
            command=lambda: _finish(False),
            width=16,
        ).pack(side=tk.LEFT, padx=10)

        self._attach_toplevel(self.result_window)
        self.result_window.wait_window()

        if self._result_continue_choice is None:
            return False
        return bool(self._result_continue_choice)

    def _refresh_result_preview(self, final_df):
        """刷新数据预览窗口。"""
        if not hasattr(self, 'result_preview_tree') or self.result_preview_tree is None:
            return

        for item in self.result_preview_tree.get_children():
            self.result_preview_tree.delete(item)

        preview_count = min(100, len(final_df))
        for i in range(preview_count):
            row = final_df.iloc[i]
            self.result_preview_tree.insert('', tk.END, values=(
                str(row.get('Name', ''))[:50],
                str(row.get('Category', '')),
                f"¥{row.get('Amount', 0):+.2f}",
                str(row.get('Date', '')),
                str(row.get('Person', '')),
                str(row.get('Source', '')),
                str(row.get('是否自动分类', '否'))
            ))
