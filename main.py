"""
main.py - 主程序入口
"""

import sys
import io
import traceback
from typing import Optional


    # --- 安全的编码修复（兼容 PyInstaller 打包）---
def _setup_utf8_encoding():
    """安全地设置 UTF-8 编码，避免 I/O 操作关闭错误"""
    try:
        # 仅当输出流存在且需要修复时才操作
        stdout = getattr(sys, "stdout", None)
        stderr = getattr(sys, "stderr", None)

        if (
            stdout is not None
            and hasattr(stdout, "buffer")
            and getattr(stdout, "encoding", None)
            and stdout.encoding.lower() != "utf-8"
        ):
            # 创建新的包装器，但保留原缓冲区的引用
            sys.stdout = io.TextIOWrapper(
                stdout.buffer,
                encoding="utf-8",
                errors="replace",  # 遇到无法编码的字符时替换
                line_buffering=True,
            )

        if (
            stderr is not None
            and hasattr(stderr, "buffer")
            and getattr(stderr, "encoding", None)
            and stderr.encoding.lower() != "utf-8"
        ):
            sys.stderr = io.TextIOWrapper(
                stderr.buffer,
                encoding="utf-8",
                errors="replace",
                line_buffering=True,
            )
    except (AttributeError, IOError, ValueError):
        # 如果设置失败，静默忽略，不影响程序主体运行
        pass


# 在模块导入时执行一次编码修复
_setup_utf8_encoding()


# 导入各个模块
try:
    from config import ConfigManager
    from data_loader import DataLoader
    from learning_engine import LearningEngine
    from user_interface import UserInterface
    from data_exporter import DataExporter
    from categorizer import BillCategorizer
    # 尝试导入GUI界面
    try:
        from gui_interface import GUIInterface
        GUI_AVAILABLE = True
    except ImportError:
        GUI_AVAILABLE = False
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保所有模块文件都在同一目录下:")
    print("  - config.py")
    print("  - data_loader.py")
    print("  - learning_engine.py")
    print("  - user_interface.py")
    print("  - data_exporter.py")
    print("  - categorizer.py")
    input("按回车键退出...")
    sys.exit(1)


def main(use_gui=True):
    """主函数"""
    try:
        # 检查必要库
        try:
            import pandas as pd
            import openpyxl
        except ImportError as e:
            print(f"❌ 缺少必要库: {e}")
            print("请运行: pip install pandas openpyxl")
            input("按回车键退出...")
            return

        # 1. 初始化配置管理器
        if not use_gui or not GUI_AVAILABLE:
            print("正在初始化配置...")
        config_manager = ConfigManager()

        # 2. 初始化各个模块
        if not use_gui or not GUI_AVAILABLE:
            print("正在初始化模块...")
        data_loader = DataLoader(config_manager)
        learning_engine = LearningEngine(config_manager)
        
        # 选择界面模式
        if use_gui and GUI_AVAILABLE:
            try:
                user_interface = GUIInterface(config_manager)
            except Exception as e:
                # GUI初始化失败，回退到CLI模式
                print(f"⚠️  GUI初始化失败: {e}")
                print("回退到命令行模式...")
                traceback.print_exc()
                user_interface = UserInterface(config_manager)
                use_gui = False
        else:
            user_interface = UserInterface(config_manager)
        
        data_exporter = DataExporter(config_manager)

        # 3. 创建主分类器
        categorizer = BillCategorizer(
            config_manager=config_manager,
            data_loader=data_loader,
            learning_engine=learning_engine,
            user_interface=user_interface,
            data_exporter=data_exporter,
        )

        # 4. 运行分类器
        if use_gui and GUI_AVAILABLE:
            # GUI模式：先显示欢迎界面，然后在后台线程中运行分类器
            # 注意：tkinter必须在主线程中运行，所以GUI主循环在主线程
            import threading
            
            # 先显示欢迎界面
            user_interface.display_welcome()
            user_interface.root.update()
            
            def run_categorizer():
                try:
                    categorizer.run()
                except Exception as e:
                    import tkinter.messagebox as msgbox
                    try:
                        msgbox.showerror("错误", f"处理过程中出错: {e}")
                    except:
                        # 如果无法显示消息框，至少打印错误
                        print(f"处理过程中出错: {e}")
                    traceback.print_exc()
            
            # 延迟启动分类器，确保GUI窗口已经显示
            def start_categorizer():
                import time
                time.sleep(0.1)  # 短暂延迟，确保GUI窗口已显示
                categorizer_thread = threading.Thread(target=run_categorizer, daemon=True)
                categorizer_thread.start()
            
            # 使用after方法在主线程中延迟启动分类器
            user_interface.root.after(100, start_categorizer)
            
            # 运行GUI主循环（必须在主线程）
            user_interface.run()
        else:
            # CLI模式：直接运行
            categorizer.run()

    except KeyboardInterrupt:
        if not (use_gui and GUI_AVAILABLE):
            print("\n\n⚠️  程序被用户中断")
    except Exception as e:
        if not (use_gui and GUI_AVAILABLE):
            print(f"\n❌ 程序运行出错: {e}")
            traceback.print_exc()
            input("\n按回车键退出...")
        else:
            # GUI模式下，尝试显示错误对话框
            try:
                import tkinter.messagebox as msgbox
                msgbox.showerror("错误", f"程序运行出错: {e}\n\n详细信息请查看控制台输出")
            except:
                # 如果无法显示GUI错误对话框，至少打印错误
                print(f"❌ 程序运行出错: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    # 检查命令行参数，支持 --cli 参数使用命令行模式
    use_gui = True
    if len(sys.argv) > 1 and '--cli' in sys.argv:
        use_gui = False
    
    main(use_gui=use_gui)
