"""
main.py - 主程序入口
"""

import sys
import traceback

# 导入各个模块
from config import ConfigManager
from data_loader import DataLoader
from learning_engine import LearningEngine
from user_interface import UserInterface
from data_exporter import DataExporter
from categorizer import BillCategorizer

def main():
    """主函数"""
    try:
        # 1. 初始化配置管理器
        print("正在初始化配置...")
        config_manager = ConfigManager()
        
        # 2. 初始化各个模块
        print("正在初始化模块...")
        data_loader = DataLoader(config_manager)
        learning_engine = LearningEngine(config_manager)
        user_interface = UserInterface(config_manager)
        data_exporter = DataExporter(config_manager)
        
        # 3. 创建主分类器
        categorizer = BillCategorizer(
            config_manager=config_manager,
            data_loader=data_loader,
            learning_engine=learning_engine,
            user_interface=user_interface,
            data_exporter=data_exporter
        )
        
        # 4. 运行分类器
        categorizer.run()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  程序被用户中断")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        traceback.print_exc()
        input("\n按回车键退出...")

if __name__ == "__main__":
    # 检查必要库
    try:
        import pandas as pd
        import openpyxl
    except ImportError as e:
        print(f"❌ 缺少必要库: {e}")
        print("请运行: pip install pandas openpyxl")
        input("按回车键退出...")
        sys.exit(1)
    
    main()