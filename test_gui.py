"""
测试GUI是否能正常显示（用于诊断PyInstaller打包问题）
"""
import sys
import os
import pytest
import tkinter as tk
from tkinter import ttk, messagebox

@pytest.mark.skipif(
    os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true',
    reason="跳过CI环境中的GUI测试"
)
def test_gui():
    """测试GUI基本功能"""
    try:
        # 检查是否在CI环境中
        is_ci = os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true'
        
        print("正在创建GUI窗口...")
        root = tk.Tk()
        root.title("GUI测试")
        root.geometry("400x300")
        
        # 确保窗口显示
        root.deiconify()
        root.lift()
        root.focus_force()
        
        # 添加测试标签
        label = ttk.Label(root, text="如果看到这个窗口，说明GUI正常工作！", font=("Arial", 12))
        label.pack(pady=50)
        
        def show_message():
            messagebox.showinfo("测试", "消息框测试成功！")
        
        btn = ttk.Button(root, text="测试消息框", command=show_message)
        btn.pack(pady=20)
        
        print("GUI窗口已创建，应该能看到窗口了")
        print("如果看不到窗口，可能是以下原因：")
        print("1. tkinter未正确打包")
        print("2. 窗口被其他窗口遮挡")
        print("3. 系统权限问题")
        
        # 在CI环境中，自动关闭窗口（2秒后）
        if is_ci:
            print("检测到CI环境，将在2秒后自动关闭窗口...")
            def close_window():
                root.quit()
                root.destroy()
            root.after(2000, close_window)
            root.mainloop()
        else:
            # 本地环境，正常等待用户交互
            root.mainloop()
        
        print("GUI测试完成")
        
    except Exception as e:
        print(f"GUI测试失败: {e}")
        import traceback
        traceback.print_exc()
        if not os.environ.get('CI'):
            input("按回车键退出...")

if __name__ == "__main__":
    test_gui()

