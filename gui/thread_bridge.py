"""
thread_bridge.py - 主线程调度与线程安全工具
"""

import queue
import threading
import tkinter as tk
from tkinter import messagebox


class ThreadBridgeMixin:
    """主线程任务队列与 widget 生命周期检查。"""

    def run_on_main_thread(self, fn, *args, default_on_stop=None, **kwargs):
        """将 callable 调度到主线程执行并同步等待结果（工作线程安全）。"""
        if threading.current_thread() is threading.main_thread():
            return fn(*args, **kwargs)
        if self.should_stop:
            return default_on_stop

        result_holder = []
        exception_holder = []
        result_ready = threading.Event()

        def wrapper():
            try:
                result_holder.append(fn(*args, **kwargs))
            except Exception as exc:
                exception_holder.append(exc)
            finally:
                result_ready.set()

        self.task_queue.put(wrapper)
        while not result_ready.wait(timeout=0.1):
            if self.should_stop:
                return default_on_stop

        if exception_holder:
            raise exception_holder[0]
        return result_holder[0] if result_holder else default_on_stop

    def _wait_for_choice_event(self):
        """等待用户选择，支持 should_stop 中断。"""
        while not self.choice_event.is_set():
            if self.should_stop:
                return
            self.choice_event.wait(timeout=0.1)

    def show_error(self, message: str):
        """在主线程显示错误对话框。"""
        if hasattr(self, 'run_on_main_thread'):
            self.run_on_main_thread(
                lambda: messagebox.showerror("错误", message),
                default_on_stop=None,
            )
        else:
            messagebox.showerror("错误", message)

    def show_info(self, message: str):
        """在主线程显示信息对话框。"""
        if hasattr(self, 'run_on_main_thread'):
            self.run_on_main_thread(
                lambda: messagebox.showinfo("提示", message),
                default_on_stop=None,
            )
        else:
            messagebox.showinfo("提示", message)

    def _widget_alive(self, widget) -> bool:
        """检查 Tk widget 是否仍存在且可用。"""
        if widget is None:
            return False
        try:
            return bool(widget.winfo_exists())
        except tk.TclError:
            return False

    def _attach_toplevel(self, window):
        """主窗口隐藏时，仍确保 Toplevel 对话框可见并置顶。"""
        try:
            if str(self.root.state()) != 'withdrawn':
                window.transient(self.root)
        except tk.TclError:
            pass
        window.deiconify()
        window.lift()
        try:
            window.attributes('-topmost', True)
            window.after(
                250,
                lambda: window.attributes('-topmost', False)
                if self._widget_alive(window) else None,
            )
        except tk.TclError:
            pass
        try:
            window.focus_force()
        except tk.TclError:
            pass

    def _process_queue(self):
        """处理队列中的任务。"""
        try:
            while True:
                task = self.task_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        self.root.after(100, self._process_queue)
