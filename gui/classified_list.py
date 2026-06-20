"""
classified_list.py - 已分类账单列表编辑与删除
"""

import tkinter as tk
from tkinter import ttk, messagebox


class ClassifiedListMixin:
    """已分类 Treeview 的双击编辑、右键删除。"""

    def _on_classified_item_double_click(self, event):
        """处理已分类账单的双击事件。"""
        selection = self.classified_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        if item_id not in self.tree_item_to_index:
            return

        data_index = self.tree_item_to_index[item_id]
        if data_index >= len(self.classified_data):
            return

        data_entry = self.classified_data[data_index]
        self._edit_classified_transaction(data_entry, item_id)

    def _on_classified_item_right_click(self, event):
        """处理已分类账单的右键点击事件。"""
        selection = self.classified_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        if item_id not in self.tree_item_to_index:
            return

        menu = tk.Menu(self.transaction_window, tearoff=0)
        menu.add_command(
            label="编辑",
            command=lambda: self._edit_classified_transaction(
                self.classified_data[self.tree_item_to_index[item_id]], item_id
            ),
        )
        menu.add_separator()
        menu.add_command(
            label="删除",
            command=lambda: self._delete_classified_transaction(item_id),
        )

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _edit_classified_transaction(self, data_entry: dict, item_id: str):
        """编辑已分类的交易。"""
        dialog = tk.Toplevel(self.transaction_window)
        dialog.title("编辑分类")
        dialog.geometry("400x350")
        dialog.transient(self.transaction_window)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (350 // 2)
        dialog.geometry(f"400x350+{x}+{y}")

        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        row = data_entry['row']
        merchant = str(row.get('交易对方', '未知商户'))
        product = str(row.get('商品', '无'))
        amount = row.get('处理后的金额', row.get('金额(元)', 0))
        date = str(row.get('交易时间', '未知时间'))
        if len(date) > 19:
            date = date[:19]

        info_text = f"时间: {date}\n商户: {merchant}\n商品: {product}\n"
        if isinstance(amount, (int, float)):
            info_text += f"金额: ¥{amount:+.2f}"
        else:
            info_text += f"金额: {amount}"

        ttk.Label(
            frame,
            text=info_text,
            style='Info.TLabel',
            justify=tk.LEFT,
        ).pack(pady=10, anchor=tk.W)

        ttk.Label(frame, text="分类:", style='Heading.TLabel').pack(pady=(10, 5), anchor=tk.W)
        category_var = tk.StringVar(value=data_entry['category'])
        base_categories = self.config.get('categories.base_categories', [])
        ttk.Combobox(
            frame,
            textvariable=category_var,
            values=base_categories,
            width=30,
            state='readonly',
        ).pack(pady=5, fill=tk.X)

        ttk.Label(frame, text="人员:", style='Heading.TLabel').pack(pady=(10, 5), anchor=tk.W)
        person_var = tk.StringVar(value=data_entry['person'])
        people_options = self.config.get('categories.people_options', [])
        ttk.Combobox(
            frame,
            textvariable=person_var,
            values=people_options,
            width=30,
            state='readonly',
        ).pack(pady=5, fill=tk.X)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)

        def save_changes():
            new_category = category_var.get()
            new_person = person_var.get()

            if not new_category or not new_person:
                messagebox.showwarning("提示", "分类和人员不能为空")
                return

            old_category = data_entry['category']
            old_person = data_entry['person']

            data_entry['category'] = new_category
            data_entry['person'] = new_person
            data_entry['is_auto'] = False

            current_values = list(self.classified_tree.item(item_id, 'values'))
            current_values[4] = new_category
            current_values[5] = new_person
            current_values[6] = '否'
            self.classified_tree.item(item_id, values=tuple(current_values))

            if self.current_processed_df is None or len(self.current_processed_df) == 0:
                if len(self.classified_data) > 0:
                    import pandas as pd

                    sorted_data = sorted(self.classified_data, key=lambda x: x['index'])
                    rows = []
                    for entry in sorted_data:
                        row_data = entry['row'].copy()
                        row_data['分类'] = entry['category']
                        row_data['人员'] = entry['person']
                        row_data['是否自动分类'] = entry.get('is_auto', False)
                        rows.append(row_data)
                    if rows:
                        self.current_processed_df = pd.DataFrame(rows)

            if self.current_processed_df is not None and len(self.current_processed_df) > 0:
                data_index = data_entry['index']
                if 0 <= data_index < len(self.current_processed_df):
                    actual_index_label = self.current_processed_df.index[data_index]
                    if '分类' in self.current_processed_df.columns:
                        self.current_processed_df.loc[actual_index_label, '分类'] = new_category
                    if '人员' in self.current_processed_df.columns:
                        self.current_processed_df.loc[actual_index_label, '人员'] = new_person
                    if '是否自动分类' in self.current_processed_df.columns:
                        self.current_processed_df.loc[actual_index_label, '是否自动分类'] = False

                    if '分类' in self.current_processed_df.columns:
                        updated_value = self.current_processed_df.loc[actual_index_label, '分类']
                        if str(updated_value) != str(new_category):
                            self.current_processed_df = self.current_processed_df.reset_index(drop=True)
                            if '分类' in self.current_processed_df.columns:
                                self.current_processed_df.iloc[
                                    data_index,
                                    self.current_processed_df.columns.get_loc('分类'),
                                ] = new_category
                            if '人员' in self.current_processed_df.columns:
                                self.current_processed_df.iloc[
                                    data_index,
                                    self.current_processed_df.columns.get_loc('人员'),
                                ] = new_person
                            if '是否自动分类' in self.current_processed_df.columns:
                                self.current_processed_df.iloc[
                                    data_index,
                                    self.current_processed_df.columns.get_loc('是否自动分类'),
                                ] = False

            if self.categorizer is not None:
                merchant_name = str(row.get('交易对方', '未知商户'))
                amount_val = row.get('处理后的金额', row.get('金额(元)', 0))
                bill_source = getattr(self.categorizer, 'current_bill_source', '其他')
                product_name = str(row.get('商品', ''))
                update_existing = (new_category != old_category or new_person != old_person)
                if isinstance(amount_val, (int, float)):
                    self.categorizer.learning_engine.learn_from_decision(
                        merchant_name,
                        new_category,
                        new_person,
                        bill_source,
                        amount_val,
                        product_name,
                        update_existing=update_existing,
                        old_category=old_category if update_existing else None,
                    )
                else:
                    self.categorizer.learning_engine.learn_from_decision(
                        merchant_name,
                        new_category,
                        new_person,
                        bill_source,
                        0,
                        product_name,
                        update_existing=update_existing,
                        old_category=old_category if update_existing else None,
                    )
                self.categorizer.learning_engine.save_data()

            if (
                self.result_window
                and self.result_window.winfo_exists()
                and self.current_processed_df is not None
                and len(self.current_processed_df) > 0
                and self.categorizer is not None
            ):
                final_df = self.categorizer.exporter.prepare_final_dataframe(
                    self.current_processed_df,
                    self.categorizer.current_bill_source,
                    self.categorizer.current_person,
                )
                self._refresh_result_preview(final_df)

            dialog.destroy()
            messagebox.showinfo("成功", "分类已更新，规则库和历史记录已同步保存")

        ttk.Button(btn_frame, text="保存", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _delete_classified_transaction(self, item_id: str):
        """删除已分类的交易。"""
        if item_id not in self.tree_item_to_index:
            return

        if not messagebox.askyesno(
            "确认", "确定要删除这条记录吗？\n注意：删除后需要重新处理才能恢复。"
        ):
            return

        data_index = self.tree_item_to_index[item_id]
        self.classified_tree.delete(item_id)

        if data_index < len(self.classified_data):
            removed_entry = self.classified_data.pop(data_index)

            if self.current_processed_df is not None:
                df_index = removed_entry['index']
                if df_index < len(self.current_processed_df):
                    actual_index_label = self.current_processed_df.index[df_index]
                    self.current_processed_df = self.current_processed_df.drop(
                        actual_index_label
                    ).reset_index(drop=True)

        self.tree_item_to_index = {}
        for i, entry in enumerate(self.classified_data):
            self.tree_item_to_index[entry['tree_item_id']] = i
            entry['index'] = len(self.classified_data) - 1 - i

        messagebox.showinfo("提示", "记录已从列表中删除")
