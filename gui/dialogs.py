"""
dialogs.py - 模态对话框与用户选择
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Any, List, Optional, Tuple


class DialogMixin:
    """账单来源、文件、人员等模态对话框。"""

    def _show_modal_dialog(self, dialog_func):
        """显示模态对话框并等待用户选择（主线程安全）。"""
        if self.should_stop:
            return None

        self.user_choice = None
        self.choice_event.clear()

        if threading.current_thread() is threading.main_thread():
            dialog_func()
        else:
            self.run_on_main_thread(dialog_func, default_on_stop=None)

        if self.should_stop:
            return None
        return self.user_choice

    def _prepare_for_continue_dialog(self):
        """继续处理前释放交易/结果窗口，避免 grab 死锁。"""
        if self.result_window:
            try:
                if self.result_window.winfo_exists():
                    self.result_window.destroy()
            except tk.TclError:
                pass
            self.result_window = None

        self._destroy_transaction_window(release_grab=True)

    def _set_choice_and_close(self, choice, window=None):
        """设置用户选择并关闭窗口。"""
        self.user_choice = choice
        if window:
            window.destroy()
        self.choice_event.set()

    def _finalize_modal_dialog(self, dialog):
        """在 grab 前确保模态框可见。"""
        self._attach_toplevel(dialog)
        dialog.grab_set()

    def select_bill_source(self) -> str:
        """选择账单来源。"""
        if self.should_stop:
            return None

        bill_sources = self.config.get('categories.bill_sources', [])

        def show_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("选择账单来源")
            dialog.geometry("400x300")

            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
            y = (dialog.winfo_screenheight() // 2) - (300 // 2)
            dialog.geometry(f"400x300+{x}+{y}")

            frame = ttk.Frame(dialog, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(
                frame,
                text="请选择账单来源：",
                style='Heading.TLabel'
            ).pack(pady=10)

            for i, source in enumerate(bill_sources, 1):
                btn = ttk.Button(
                    frame,
                    text=f"{i}. {source}",
                    width=30,
                    command=lambda s=source: self._set_choice_and_close(s, dialog)
                )
                btn.pack(pady=5)

            dialog.protocol("WM_DELETE_WINDOW", lambda: self._set_choice_and_close(None, dialog))
            print("📋 请在弹出窗口中选择账单来源…")
            self._finalize_modal_dialog(dialog)
            dialog.wait_window()

        result = self._show_modal_dialog(show_dialog)
        if result is None:
            return None
        return result

    def display_file_list(self, files: List[str]) -> Optional[str]:
        """显示文件列表并让用户选择。"""
        if self.should_stop:
            return None

        if not files:
            self.run_on_main_thread(
                lambda: messagebox.showwarning(
                    "提示", "未找到账单文件\n请将账单文件放在程序目录下"
                ),
                default_on_stop=None,
            )
            return None

        def show_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("选择账单文件")
            dialog.geometry("600x400")

            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (600 // 2)
            y = (dialog.winfo_screenheight() // 2) - (400 // 2)
            dialog.geometry(f"600x400+{x}+{y}")

            frame = ttk.Frame(dialog, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(
                frame,
                text="请选择账单文件：",
                style='Heading.TLabel'
            ).pack(pady=10)

            listbox_frame = ttk.Frame(frame)
            listbox_frame.pack(fill=tk.BOTH, expand=True, pady=10)

            scrollbar = ttk.Scrollbar(listbox_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=listbox.yview)

            for file in files:
                listbox.insert(tk.END, file)

            if files:
                listbox.selection_set(0)
                listbox.see(0)

            btn_frame = ttk.Frame(frame)
            btn_frame.pack(pady=10)

            def select_file():
                selection = listbox.curselection()
                if selection:
                    selected_file = files[selection[0]]
                    self._set_choice_and_close(selected_file, dialog)
                else:
                    messagebox.showwarning("提示", "请选择一个文件")

            def browse_file():
                file_path = filedialog.askopenfilename(
                    title="选择账单文件",
                    filetypes=[
                        ("Excel文件", "*.xlsx *.xls"),
                        ("CSV文件", "*.csv"),
                        ("所有文件", "*.*")
                    ]
                )
                if file_path:
                    self._set_choice_and_close(file_path, dialog)

            ttk.Button(btn_frame, text="选择", command=select_file).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="浏览文件", command=browse_file).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="取消", command=lambda: self._set_choice_and_close(None, dialog)).pack(side=tk.LEFT, padx=5)

            listbox.bind('<Double-Button-1>', lambda e: select_file())

            dialog.protocol("WM_DELETE_WINDOW", lambda: self._set_choice_and_close(None, dialog))
            self._finalize_modal_dialog(dialog)
            dialog.wait_window()

        return self._show_modal_dialog(show_dialog)

    def select_person_mode(self) -> Tuple[str, str]:
        """选择人员模式。"""
        if self.should_stop:
            return ('', 'per_transaction')

        def show_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("选择人员分配方式")
            dialog.geometry("400x200")

            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
            y = (dialog.winfo_screenheight() // 2) - (200 // 2)
            dialog.geometry(f"400x200+{x}+{y}")

            frame = ttk.Frame(dialog, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(
                frame,
                text="请选择人员分配方式：",
                style='Heading.TLabel'
            ).pack(pady=10)

            result = [None, None]

            def select_unified():
                # 先释放外层 grab，再打开人员选择，避免嵌套模态冲突
                try:
                    dialog.grab_release()
                except tk.TclError:
                    pass
                try:
                    person = self._select_unified_person()
                except Exception as exc:
                    messagebox.showerror("错误", f"选择人员失败：{exc}")
                    try:
                        if dialog.winfo_exists():
                            dialog.grab_set()
                    except tk.TclError:
                        pass
                    return
                if person:
                    result[0] = person
                    result[1] = 'fixed'
                    self._set_choice_and_close(tuple(result), dialog)

            def select_per_transaction():
                result[0] = ''
                result[1] = 'per_transaction'
                self._set_choice_and_close(tuple(result), dialog)

            ttk.Button(
                frame,
                text="1. 所有记录统一人员",
                command=select_unified,
                width=30
            ).pack(pady=5)

            ttk.Button(
                frame,
                text="2. 每条记录单独选择",
                command=select_per_transaction,
                width=30
            ).pack(pady=5)

            dialog.protocol("WM_DELETE_WINDOW", lambda: self._set_choice_and_close(None, dialog))
            self._finalize_modal_dialog(dialog)
            dialog.wait_window()

        result = self._show_modal_dialog(show_dialog)
        if result is None:
            return '', 'per_transaction'
        return result

    def _select_unified_person(self) -> str:
        """选择统一人员（支持新增）。"""
        people_options = self.config.get('categories.people_options', [])

        def show_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("选择统一人员")
            dialog.geometry("400x400")

            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
            y = (dialog.winfo_screenheight() // 2) - (400 // 2)
            dialog.geometry(f"400x400+{x}+{y}")

            frame = ttk.Frame(dialog, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(
                frame,
                text="请选择统一人员：",
                style='Heading.TLabel'
            ).pack(pady=10)

            list_frame = ttk.Frame(frame)
            list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

            canvas = tk.Canvas(list_frame, height=200)
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            for i, person in enumerate(people_options, 1):
                btn = ttk.Button(
                    scrollable_frame,
                    text=f"{i}. {person}",
                    width=30,
                    command=lambda p=person: self._set_choice_and_close(p, dialog)
                )
                btn.pack(pady=2)

            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            def add_new_person():
                def show_add_dialog():
                    add_dialog = tk.Toplevel(dialog)
                    add_dialog.title("新增人员")
                    add_dialog.geometry("350x120")

                    add_dialog.update_idletasks()
                    ax = (add_dialog.winfo_screenwidth() // 2) - (350 // 2)
                    ay = (add_dialog.winfo_screenheight() // 2) - (120 // 2)
                    add_dialog.geometry(f"350x120+{ax}+{ay}")

                    add_frame = ttk.Frame(add_dialog, padding="20")
                    add_frame.pack(fill=tk.BOTH, expand=True)

                    ttk.Label(add_frame, text="请输入人员名称：", style='Info.TLabel').pack(pady=5)

                    entry = ttk.Entry(add_frame, width=30, font=("Arial", 10))
                    entry.pack(pady=10)
                    entry.focus()

                    def confirm_add():
                        new_person = entry.get().strip()
                        if new_person:
                            current_people = self.config.get('categories.people_options', [])
                            if new_person not in current_people:
                                current_people.append(new_person)
                                self.config.set('categories.people_options', current_people)
                                self.config.save_custom_config()
                            add_dialog.destroy()
                            dialog.destroy()
                            refreshed = self._select_unified_person()
                            if refreshed:
                                self._set_choice_and_close(refreshed, None)
                        else:
                            messagebox.showwarning("提示", "人员名称不能为空")

                    def cancel_add():
                        add_dialog.destroy()

                    btn_frame = ttk.Frame(add_frame)
                    btn_frame.pack(pady=5)

                    ttk.Button(btn_frame, text="确定", command=confirm_add).pack(side=tk.LEFT, padx=5)
                    ttk.Button(btn_frame, text="取消", command=cancel_add).pack(side=tk.LEFT, padx=5)

                    entry.bind('<Return>', lambda e: confirm_add())
                    add_dialog.protocol("WM_DELETE_WINDOW", cancel_add)
                    self._attach_toplevel(add_dialog)
                    add_dialog.grab_set()
                    add_dialog.wait_window()

                show_add_dialog()

            ttk.Button(
                frame,
                text="+ 新增人员",
                command=add_new_person,
                width=30
            ).pack(pady=5)

            dialog.protocol("WM_DELETE_WINDOW", lambda: self._set_choice_and_close(None, dialog))
            self._finalize_modal_dialog(dialog)
            dialog.wait_window()

        result = self._show_modal_dialog(show_dialog)
        if result is None:
            people_options = self.config.get('categories.people_options', [])
            return people_options[0] if people_options else "家庭公用"
        return result

    def select_person_for_transaction(self, merchant: str) -> str:
        """为单条交易选择人员（支持新增）。"""
        people_options = self.config.get('categories.people_options', [])

        def show_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("选择人员")
            dialog.geometry("400x400")

            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
            y = (dialog.winfo_screenheight() // 2) - (400 // 2)
            dialog.geometry(f"400x400+{x}+{y}")

            frame = ttk.Frame(dialog, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(
                frame,
                text=f"交易: {merchant}",
                style='Heading.TLabel'
            ).pack(pady=5)

            ttk.Label(
                frame,
                text="请选择人员：",
                style='Info.TLabel'
            ).pack(pady=10)

            list_frame = ttk.Frame(frame)
            list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

            canvas = tk.Canvas(list_frame, height=200)
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            for i, person in enumerate(people_options, 1):
                btn = ttk.Button(
                    scrollable_frame,
                    text=f"{i}. {person}",
                    width=30,
                    command=lambda p=person: self._set_choice_and_close(p, dialog)
                )
                btn.pack(pady=2)

            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            def add_new_person():
                def show_add_dialog():
                    add_dialog = tk.Toplevel(dialog)
                    add_dialog.title("新增人员")
                    add_dialog.geometry("350x120")

                    add_dialog.update_idletasks()
                    ax = (add_dialog.winfo_screenwidth() // 2) - (350 // 2)
                    ay = (add_dialog.winfo_screenheight() // 2) - (120 // 2)
                    add_dialog.geometry(f"350x120+{ax}+{ay}")

                    add_frame = ttk.Frame(add_dialog, padding="20")
                    add_frame.pack(fill=tk.BOTH, expand=True)

                    ttk.Label(add_frame, text="请输入人员名称：", style='Info.TLabel').pack(pady=5)

                    entry = ttk.Entry(add_frame, width=30, font=("Arial", 10))
                    entry.pack(pady=10)
                    entry.focus()

                    def confirm_add():
                        new_person = entry.get().strip()
                        if new_person:
                            current_people = self.config.get('categories.people_options', [])
                            if new_person not in current_people:
                                current_people.append(new_person)
                                self.config.set('categories.people_options', current_people)
                                self.config.save_custom_config()
                            add_dialog.destroy()
                            dialog.destroy()
                            refreshed = self.select_person_for_transaction(merchant)
                            if refreshed:
                                self._set_choice_and_close(refreshed, None)
                        else:
                            messagebox.showwarning("提示", "人员名称不能为空")

                    def cancel_add():
                        add_dialog.destroy()

                    btn_frame = ttk.Frame(add_frame)
                    btn_frame.pack(pady=5)

                    ttk.Button(btn_frame, text="确定", command=confirm_add).pack(side=tk.LEFT, padx=5)
                    ttk.Button(btn_frame, text="取消", command=cancel_add).pack(side=tk.LEFT, padx=5)

                    entry.bind('<Return>', lambda e: confirm_add())
                    add_dialog.protocol("WM_DELETE_WINDOW", cancel_add)
                    self._attach_toplevel(add_dialog)
                    add_dialog.grab_set()
                    add_dialog.wait_window()

                show_add_dialog()

            ttk.Button(
                frame,
                text="+ 新增人员",
                command=add_new_person,
                width=30
            ).pack(pady=5)

            dialog.protocol("WM_DELETE_WINDOW", lambda: self._set_choice_and_close(None, dialog))
            self._finalize_modal_dialog(dialog)
            dialog.wait_window()

        result = self._show_modal_dialog(show_dialog)
        if result is None:
            people_options = self.config.get('categories.people_options', [])
            return people_options[0] if people_options else "家庭公用"
        return result

    def get_validated_input(self, prompt: str, input_type: str = 'number',
                           valid_range: Tuple = None, valid_options: List = None) -> Any:
        """获取并验证用户输入。"""
        if input_type == 'category_choice':
            self.user_choice = None
            self.choice_event.clear()
            self._wait_for_choice_event()
            if self.should_stop:
                return 'q'
            return self.user_choice

        elif input_type == 'text':
            def show_input_dialog():
                dialog = tk.Toplevel(self.root)
                dialog.title("输入新分类")
                dialog.geometry("400x150")

                dialog.update_idletasks()
                x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
                y = (dialog.winfo_screenheight() // 2) - (150 // 2)
                dialog.geometry(f"400x150+{x}+{y}")

                frame = ttk.Frame(dialog, padding="20")
                frame.pack(fill=tk.BOTH, expand=True)

                ttk.Label(frame, text=prompt, font=("Arial", 10)).pack(pady=5)

                entry = ttk.Entry(frame, width=40, font=("Arial", 10))
                entry.pack(pady=10)
                entry.focus()

                def confirm():
                    text = entry.get().strip()
                    if text:
                        self._set_choice_and_close(text, dialog)
                    else:
                        messagebox.showwarning("提示", "输入不能为空")

                def cancel():
                    self._set_choice_and_close(None, dialog)

                btn_frame = ttk.Frame(frame)
                btn_frame.pack(pady=5)

                ttk.Button(btn_frame, text="确定", command=confirm).pack(side=tk.LEFT, padx=5)
                ttk.Button(btn_frame, text="取消", command=cancel).pack(side=tk.LEFT, padx=5)

                entry.bind('<Return>', lambda e: confirm())
                dialog.protocol("WM_DELETE_WINDOW", cancel)
                self._finalize_modal_dialog(dialog)
                dialog.wait_window()

            result = self._show_modal_dialog(show_input_dialog)
            if result is None:
                return "其他"
            return result

        return None

    def ask_continue_processing(self) -> bool:
        """询问用户是否继续处理下一个账单。"""
        if self.should_stop:
            return False

        self._prepare_for_continue_dialog()

        def show_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("继续处理")
            dialog.geometry("400x200")

            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
            y = (dialog.winfo_screenheight() // 2) - (200 // 2)
            dialog.geometry(f"400x200+{x}+{y}")

            frame = ttk.Frame(dialog, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(
                frame,
                text="✨ 当前账单处理完成！",
                style='Heading.TLabel'
            ).pack(pady=10)

            ttk.Label(
                frame,
                text="是否继续处理下一个账单？",
                style='Info.TLabel'
            ).pack(pady=10)

            btn_frame = ttk.Frame(frame)
            btn_frame.pack(pady=20)

            ttk.Button(
                btn_frame,
                text="是，继续处理",
                command=lambda: self._set_choice_and_close(True, dialog),
                width=15
            ).pack(side=tk.LEFT, padx=10)

            ttk.Button(
                btn_frame,
                text="否，退出程序",
                command=lambda: self._set_choice_and_close(False, dialog),
                width=15
            ).pack(side=tk.LEFT, padx=10)

            dialog.protocol("WM_DELETE_WINDOW", lambda: self._set_choice_and_close(False, dialog))
            self._finalize_modal_dialog(dialog)
            dialog.wait_window()

        result = self._show_modal_dialog(show_dialog)
        return result if result is not None else False
