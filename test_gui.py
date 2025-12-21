"""
测试GUI是否能正常显示（用于诊断PyInstaller打包问题）
"""
import sys
import tkinter as tk
from tkinter import ttk, messagebox

def test_gui():
    """测试GUI基本功能"""
    try:
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
        
        root.mainloop()
        print("GUI测试完成")
        
    except Exception as e:
        print(f"GUI测试失败: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")

if __name__ == "__main__":
    test_gui()

