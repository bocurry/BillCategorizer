"""
gui_interface.py - GUI用户界面模块
使用tkinter实现图形用户界面，替代命令行交互
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Any, Optional, List, Tuple, Dict
import threading
import queue


class GUIInterface:
    """GUI界面管理器 - 实现与UserInterface相同的接口"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        
        # 创建主窗口
        try:
            self.root = tk.Tk()
            self.root.title("账单自动分类助手")
            self.root.geometry("800x600")
            self.root.resizable(True, True)
            
            # 确保窗口在PyInstaller打包后也能正常显示
            self.root.deiconify()  # 确保窗口显示
            self.root.lift()  # 将窗口置于最前
            self.root.focus_force()  # 强制获取焦点
        except Exception as e:
            # 如果GUI初始化失败，抛出异常以便调试
            raise RuntimeError(f"GUI初始化失败: {e}")
        
        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 配置颜色方案
        self.style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        self.style.configure('Heading.TLabel', font=('Arial', 12, 'bold'))
        self.style.configure('Info.TLabel', font=('Arial', 10))
        
        # 配置按钮样式
        self.style.configure('Action.TButton', padding=10)
        
        # 用户选择结果存储（用于阻塞操作）
        self.user_choice = None
        self.choice_event = threading.Event()
        
        # 使用队列来处理异步操作
        self.task_queue = queue.Queue()
        
        # 当前交易处理窗口
        self.transaction_window = None
        self.progress_var = None
        self.progress_label = None
        
        # 已分类账单列表
        self.classified_list = []  # 存储已分类的交易信息
        self.classified_tree = None  # Treeview组件
        
        # 结果显示窗口
        self.result_window = None
        
    def display_welcome(self):
        """显示欢迎信息"""
        # 清除现有内容
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 创建欢迎界面
        welcome_frame = ttk.Frame(self.root, padding="20")
        welcome_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(
            welcome_frame, 
            text="账单自动分类助手", 
            style='Title.TLabel'
        )
        title_label.pack(pady=30)
        
        # 说明信息
        info_text = """输出包含：Name, Category, Amount, Date, Person, Source
        
本程序将帮助您：
• 自动分类账单交易记录
• 学习您的分类习惯
• 导出结构化数据"""
        info_label = ttk.Label(
            welcome_frame, 
            text=info_text,
            style='Info.TLabel',
            justify=tk.LEFT
        )
        info_label.pack(pady=20, padx=20)
        
        # 开始按钮（实际上不需要，因为后续会自动进入流程）
        # 但为了兼容性，我们显示欢迎信息后立即进入下一步
        
    def _show_modal_dialog(self, dialog_func):
        """显示模态对话框并等待用户选择"""
        self.user_choice = None
        self.choice_event.clear()
        
        # 直接在主线程中显示对话框（tkinter需要主线程）
        # dialog_func内部会调用wait_window()，这会阻塞直到窗口关闭
        dialog_func()
        
        # 等待用户选择（通过事件确保选择已设置）
        self.choice_event.wait()
        return self.user_choice
    
    def select_bill_source(self) -> str:
        """选择账单来源"""
        bill_sources = self.config.get('categories.bill_sources', [])
        
        def show_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("选择账单来源")
            dialog.geometry("400x300")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 居中显示
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
            
            selected_source = [None]
            
            for i, source in enumerate(bill_sources, 1):
                btn = ttk.Button(
                    frame,
                    text=f"{i}. {source}",
                    width=30,
                    command=lambda s=source: self._set_choice_and_close(s, dialog)
                )
                btn.pack(pady=5)
            
            dialog.protocol("WM_DELETE_WINDOW", lambda: self._set_choice_and_close(None, dialog))
            dialog.wait_window()
        
        result = self._show_modal_dialog(show_dialog)
        if result is None:
            return bill_sources[0] if bill_sources else "其他"
        return result
    
    def _set_choice_and_close(self, choice, window=None):
        """设置用户选择并关闭窗口"""
        self.user_choice = choice
        if window:
            window.destroy()
        self.choice_event.set()
    
    def display_file_list(self, files: List[str]) -> Optional[str]:
        """显示文件列表并让用户选择"""
        if not files:
            messagebox.showwarning("提示", "未找到账单文件\n请将账单文件放在程序目录下")
            return None
        
        def show_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("选择账单文件")
            dialog.geometry("600x400")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 居中显示
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
            
            # 文件列表
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
            
            # 按钮区域
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
            
            # 双击选择
            listbox.bind('<Double-Button-1>', lambda e: select_file())
            
            dialog.protocol("WM_DELETE_WINDOW", lambda: self._set_choice_and_close(None, dialog))
            dialog.wait_window()
        
        return self._show_modal_dialog(show_dialog)
    
    def select_person_mode(self) -> Tuple[str, str]:
        """选择人员模式"""
        def show_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("选择人员分配方式")
            dialog.geometry("400x200")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 居中显示
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
                person = self._select_unified_person()
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
            dialog.wait_window()
        
        result = self._show_modal_dialog(show_dialog)
        if result is None:
            return '', 'per_transaction'
        return result
    
    def _select_unified_person(self) -> str:
        """选择统一人员（支持新增）"""
        people_options = self.config.get('categories.people_options', [])
        
        def show_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("选择统一人员")
            dialog.geometry("400x400")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 居中显示
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
            
            # 人员列表区域（可滚动）
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
            
            # 新增人员按钮
            def add_new_person():
                def show_add_dialog():
                    add_dialog = tk.Toplevel(dialog)
                    add_dialog.title("新增人员")
                    add_dialog.geometry("350x120")
                    add_dialog.transient(dialog)
                    add_dialog.grab_set()
                    
                    add_dialog.update_idletasks()
                    x = (add_dialog.winfo_screenwidth() // 2) - (350 // 2)
                    y = (add_dialog.winfo_screenheight() // 2) - (120 // 2)
                    add_dialog.geometry(f"350x120+{x}+{y}")
                    
                    add_frame = ttk.Frame(add_dialog, padding="20")
                    add_frame.pack(fill=tk.BOTH, expand=True)
                    
                    ttk.Label(add_frame, text="请输入人员名称：", style='Info.TLabel').pack(pady=5)
                    
                    entry = ttk.Entry(add_frame, width=30, font=("Arial", 10))
                    entry.pack(pady=10)
                    entry.focus()
                    
                    def confirm_add():
                        new_person = entry.get().strip()
                        if new_person:
                            # 添加到配置
                            current_people = self.config.get('categories.people_options', [])
                            if new_person not in current_people:
                                current_people.append(new_person)
                                self.config.set('categories.people_options', current_people)
                                self.config.save_custom_config()
                            add_dialog.destroy()
                            dialog.destroy()
                            # 重新显示对话框以刷新列表
                            result = self._select_unified_person()
                            if result:
                                self._set_choice_and_close(result, None)
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
                    add_dialog.wait_window()
                
                show_add_dialog()
            
            ttk.Button(
                frame,
                text="+ 新增人员",
                command=add_new_person,
                width=30
            ).pack(pady=5)
            
            dialog.protocol("WM_DELETE_WINDOW", lambda: self._set_choice_and_close(None, dialog))
            dialog.wait_window()
        
        result = self._show_modal_dialog(show_dialog)
        if result is None:
            people_options = self.config.get('categories.people_options', [])
            return people_options[0] if people_options else "家庭公用"
        return result
    
    def select_person_for_transaction(self, merchant: str) -> str:
        """为单条交易选择人员（支持新增）"""
        people_options = self.config.get('categories.people_options', [])
        
        def show_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("选择人员")
            dialog.geometry("400x400")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 居中显示
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
            
            # 人员列表区域（可滚动）
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
            
            # 新增人员按钮
            def add_new_person():
                def show_add_dialog():
                    add_dialog = tk.Toplevel(dialog)
                    add_dialog.title("新增人员")
                    add_dialog.geometry("350x120")
                    add_dialog.transient(dialog)
                    add_dialog.grab_set()
                    
                    add_dialog.update_idletasks()
                    x = (add_dialog.winfo_screenwidth() // 2) - (350 // 2)
                    y = (add_dialog.winfo_screenheight() // 2) - (120 // 2)
                    add_dialog.geometry(f"350x120+{x}+{y}")
                    
                    add_frame = ttk.Frame(add_dialog, padding="20")
                    add_frame.pack(fill=tk.BOTH, expand=True)
                    
                    ttk.Label(add_frame, text="请输入人员名称：", style='Info.TLabel').pack(pady=5)
                    
                    entry = ttk.Entry(add_frame, width=30, font=("Arial", 10))
                    entry.pack(pady=10)
                    entry.focus()
                    
                    def confirm_add():
                        new_person = entry.get().strip()
                        if new_person:
                            # 添加到配置
                            current_people = self.config.get('categories.people_options', [])
                            if new_person not in current_people:
                                current_people.append(new_person)
                                self.config.set('categories.people_options', current_people)
                                self.config.save_custom_config()
                            add_dialog.destroy()
                            dialog.destroy()
                            # 重新显示对话框以刷新列表
                            result = self.select_person_for_transaction(merchant)
                            if result:
                                self._set_choice_and_close(result, None)
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
                    add_dialog.wait_window()
                
                show_add_dialog()
            
            ttk.Button(
                frame,
                text="+ 新增人员",
                command=add_new_person,
                width=30
            ).pack(pady=5)
            
            dialog.protocol("WM_DELETE_WINDOW", lambda: self._set_choice_and_close(None, dialog))
            dialog.wait_window()
        
        result = self._show_modal_dialog(show_dialog)
        if result is None:
            people_options = self.config.get('categories.people_options', [])
            return people_options[0] if people_options else "家庭公用"
        return result
    
    def display_transaction(self, idx: int, total: int, row: dict):
        """显示交易信息"""
        # 如果交易窗口不存在，创建它
        if self.transaction_window is None or not self.transaction_window.winfo_exists():
            self._create_transaction_window()
        
        # 更新交易信息
        merchant = str(row.get('交易对方', '未知商户'))
        product = str(row.get('商品', '无'))
        tx_type = str(row.get('交易类型', '未知类型'))
        amount = row.get('处理后的金额', row.get('金额(元)', 0))
        date = row.get('交易时间', '未知时间')
        
        # 更新窗口内容
        if hasattr(self, 'transaction_info_frame'):
            for widget in self.transaction_info_frame.winfo_children():
                widget.destroy()
            
            # 交易编号
            ttk.Label(
                self.transaction_info_frame,
                text=f"交易 {idx}/{total}",
                style='Title.TLabel'
            ).pack(pady=5)
            
            # 交易详情（显示时间、商户、商品）
            info_lines = [
                f"时间: {date}",
                f"商户: {merchant}",
                f"商品: {product}"
            ]
            if isinstance(amount, (int, float)):
                info_lines.append(f"金额: ¥{amount:+.2f}")
            else:
                info_lines.append(f"金额: {amount}")
            
            info_text = "\n".join(info_lines)
            
            ttk.Label(
                self.transaction_info_frame,
                text=info_text,
                style='Info.TLabel',
                justify=tk.LEFT
            ).pack(pady=5, anchor=tk.W)
        
        # 更新进度
        if self.progress_var:
            progress = (idx / total * 100) if total > 0 else 0
            self.progress_var.set(progress)
        
        if self.progress_label:
            self.progress_label.config(text=f"进度: {idx}/{total} ({progress:.1f}%)")
        
        # 确保窗口可见
        self.transaction_window.update()
    
    def _create_transaction_window(self):
        """创建交易处理窗口"""
        self.transaction_window = tk.Toplevel(self.root)
        self.transaction_window.title("处理交易")
        self.transaction_window.geometry("700x600")
        
        # 居中显示
        self.transaction_window.update_idletasks()
        x = (self.transaction_window.winfo_screenwidth() // 2) - (1000 // 2)
        y = (self.transaction_window.winfo_screenheight() // 2) - (700 // 2)
        self.transaction_window.geometry(f"1000x700+{x}+{y}")
        
        # 进度条
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
        
        # 交易信息区域
        info_frame = ttk.LabelFrame(self.transaction_window, text="当前交易信息", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.transaction_info_frame = ttk.Frame(info_frame)
        self.transaction_info_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建左右分栏布局
        main_container = ttk.Frame(self.transaction_window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧：分类选择区域
        left_frame = ttk.Frame(main_container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.classification_frame = ttk.LabelFrame(left_frame, text="分类选择", padding="10")
        self.classification_frame.pack(fill=tk.BOTH, expand=True)
        
        # 右侧：已分类账单区域
        right_frame = ttk.Frame(main_container)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        classified_frame = ttk.LabelFrame(right_frame, text="已分类账单", padding="10")
        classified_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建已分类账单的Treeview
        classified_tree_frame = ttk.Frame(classified_frame)
        classified_tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # 滚动条
        classified_scrollbar_y = ttk.Scrollbar(classified_tree_frame, orient=tk.VERTICAL)
        classified_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        classified_scrollbar_x = ttk.Scrollbar(classified_tree_frame, orient=tk.HORIZONTAL)
        classified_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview
        self.classified_tree = ttk.Treeview(
            classified_tree_frame,
            columns=('时间', '商户', '商品', '金额', '分类', '人员'),
            show='headings',
            yscrollcommand=classified_scrollbar_y.set,
            xscrollcommand=classified_scrollbar_x.set,
            height=15
        )
        
        # 设置列标题和宽度
        self.classified_tree.heading('时间', text='时间')
        self.classified_tree.heading('商户', text='商户')
        self.classified_tree.heading('商品', text='商品')
        self.classified_tree.heading('金额', text='金额')
        self.classified_tree.heading('分类', text='分类')
        self.classified_tree.heading('人员', text='人员')
        
        self.classified_tree.column('时间', width=120)
        self.classified_tree.column('商户', width=150)
        self.classified_tree.column('商品', width=150)
        self.classified_tree.column('金额', width=80)
        self.classified_tree.column('分类', width=100)
        self.classified_tree.column('人员', width=80)
        
        self.classified_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        classified_scrollbar_y.config(command=self.classified_tree.yview)
        classified_scrollbar_x.config(command=self.classified_tree.xview)
        
        # 按钮区域
        self.button_frame = ttk.Frame(self.transaction_window, padding="10")
        self.button_frame.pack(fill=tk.X, pady=5)
    
    def display_classification_menu(self, suggestions: dict, base_categories: list):
        """显示分类选择菜单"""
        # 确保交易窗口存在
        if self.transaction_window is None or not self.transaction_window.winfo_exists():
            self._create_transaction_window()
        
        # 清除现有分类选择区域
        for widget in self.classification_frame.winfo_children():
            widget.destroy()
        
        # 清除按钮区域
        for widget in self.button_frame.winfo_children():
            widget.destroy()
        
        # 系统建议
        if suggestions:
            suggestions_frame = ttk.Frame(self.classification_frame)
            suggestions_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(
                suggestions_frame,
                text="系统建议:",
                style='Heading.TLabel'
            ).pack(anchor=tk.W)
            
            suggestions_list = list(suggestions.items())
            for i, (category, reason) in enumerate(suggestions_list, 1):
                btn_text = f"[{i}] {category} ← {reason}"
                btn = ttk.Button(
                    suggestions_frame,
                    text=btn_text,
                    command=lambda c=category, idx=i: self._set_category_choice(idx),
                    width=50
                )
                btn.pack(anchor=tk.W, pady=2, padx=20)
        
        # 基础分类
        base_frame = ttk.Frame(self.classification_frame)
        base_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(
            base_frame,
            text="基础分类:",
            style='Heading.TLabel'
        ).pack(anchor=tk.W)
        
        # 使用滚动区域（增加高度以显示所有分类）
        # 使用网格布局让按钮多列显示，充分利用空间
        canvas = tk.Canvas(base_frame, height=250)
        scrollbar = ttk.Scrollbar(base_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 使用网格布局，每行显示2列按钮，充分利用空间
        start_idx = len(suggestions) + 1
        for i, category in enumerate(base_categories):
            idx = start_idx + i
            row = i // 2  # 每行2个按钮
            col = i % 2   # 列位置（0或1）
            
            btn = ttk.Button(
                scrollable_frame,
                text=f"[{idx}] {category}",
                command=lambda c=category, idx=idx: self._set_category_choice(idx),
                width=30
            )
            btn.grid(row=row, column=col, sticky=tk.W+tk.E, padx=10, pady=2)
        
        # 配置列权重，让按钮均匀分布
        scrollable_frame.columnconfigure(0, weight=1)
        scrollable_frame.columnconfigure(1, weight=1)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 操作按钮
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
        
        self.transaction_window.update()
    
    def _set_category_choice(self, choice):
        """设置分类选择"""
        self.user_choice = choice
        self.choice_event.set()
    
    def add_classified_transaction(self, row: dict, category: str, person: str):
        """添加已分类的交易到列表中"""
        if self.classified_tree is None:
            return
        
        # 获取交易信息
        date = str(row.get('交易时间', '未知时间'))
        # 如果日期太长，截取前19个字符（日期时间格式）
        if len(date) > 19:
            date = date[:19]
        
        merchant = str(row.get('交易对方', '未知商户'))
        product = str(row.get('商品', '无'))
        amount = row.get('处理后的金额', row.get('金额(元)', 0))
        
        # 格式化金额
        if isinstance(amount, (int, float)):
            amount_str = f"¥{amount:+.2f}"
        else:
            amount_str = str(amount)
        
        # 添加到Treeview（插入到顶部）
        self.classified_tree.insert(
            '',
            0,  # 插入到顶部
            values=(date, merchant, product, amount_str, category, person)
        )
        
        # 自动滚动到顶部显示最新添加的记录
        children = self.classified_tree.get_children()
        if children:
            self.classified_tree.see(children[0])
    
    def get_validated_input(self, prompt: str, input_type: str = 'number', 
                           valid_range: Tuple = None, valid_options: List = None) -> Any:
        """获取并验证用户输入"""
        # 对于category_choice类型，已经在display_classification_menu中处理
        if input_type == 'category_choice':
            self.user_choice = None
            self.choice_event.clear()
            self.choice_event.wait()
            return self.user_choice
        
        # 对于text类型（新分类输入）
        elif input_type == 'text':
            def show_input_dialog():
                dialog = tk.Toplevel(self.root)
                dialog.title("输入新分类")
                dialog.geometry("400x150")
                dialog.transient(self.root)
                dialog.grab_set()
                
                # 居中显示
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
                        # 新分类会被添加到基础分类（在categorizer.py中处理）
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
                dialog.wait_window()
            
            result = self._show_modal_dialog(show_input_dialog)
            if result is None:
                return "其他"
            return result
        
        # 其他类型暂时返回None（应该不会用到）
        return None
    
    def display_progress(self, current: int, total: int):
        """显示处理进度"""
        if self.progress_var and self.progress_label:
            progress = (current / total * 100) if total > 0 else 0
            self.progress_var.set(progress)
            self.progress_label.config(text=f"进度: {current}/{total} ({progress:.1f}%)")
            self.root.update_idletasks()
    
    def show_results(self, final_df, output_file, stats, engine_stats):
        """显示处理结果（新增方法，用于GUI显示）"""
        # 创建结果显示窗口
        if self.result_window and self.result_window.winfo_exists():
            self.result_window.destroy()
        
        self.result_window = tk.Toplevel(self.root)
        self.result_window.title("处理结果")
        self.result_window.geometry("900x700")
        
        # 居中显示
        self.result_window.update_idletasks()
        x = (self.result_window.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.result_window.winfo_screenheight() // 2) - (700 // 2)
        self.result_window.geometry(f"900x700+{x}+{y}")
        
        # 创建Notebook（标签页）
        notebook = ttk.Notebook(self.result_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 数据预览标签页
        preview_frame = ttk.Frame(notebook, padding="10")
        notebook.add(preview_frame, text="数据预览")
        
        # 创建表格
        tree_frame = ttk.Frame(preview_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar_y = ttk.Scrollbar(tree_frame)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        tree = ttk.Treeview(
            tree_frame,
            columns=('Name', 'Category', 'Amount', 'Date', 'Person', 'Source'),
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
        
        tree.column('Name', width=200)
        tree.column('Category', width=100)
        tree.column('Amount', width=100)
        tree.column('Date', width=100)
        tree.column('Person', width=100)
        tree.column('Source', width=80)
        
        scrollbar_y.config(command=tree.yview)
        scrollbar_x.config(command=tree.xview)
        
        # 插入数据
        preview_count = min(100, len(final_df))  # 最多显示100条
        for i in range(preview_count):
            row = final_df.iloc[i]
            tree.insert('', tk.END, values=(
                str(row.get('Name', ''))[:50],
                str(row.get('Category', '')),
                f"¥{row.get('Amount', 0):+.2f}",
                str(row.get('Date', '')),
                str(row.get('Person', '')),
                str(row.get('Source', ''))
            ))
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 统计信息标签页
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
        
        stats_label = ttk.Label(
            stats_frame,
            text=stats_text.strip(),
            font=("Arial", 10),
            justify=tk.LEFT
        )
        stats_label.pack(anchor=tk.W, pady=10)
        
        # 关闭按钮
        btn_frame = ttk.Frame(self.result_window, padding="10")
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(
            btn_frame,
            text="关闭",
            command=self.result_window.destroy
        ).pack()
        
        messagebox.showinfo("处理完成", f"账单已处理完成！\n\n导出文件：{output_file}")
    
    def run(self):
        """运行GUI主循环"""
        # 定期处理队列中的任务
        self._process_queue()
        self.root.mainloop()
    
    def _process_queue(self):
        """处理队列中的任务"""
        try:
            while True:
                task = self.task_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        # 每100ms检查一次队列
        self.root.after(100, self._process_queue)
    
    def destroy(self):
        """销毁窗口"""
        if self.root:
            self.root.destroy()

