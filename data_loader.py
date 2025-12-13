"""
data_loader.py - 数据加载模块
负责读取和处理Excel账单文件
"""

import pandas as pd
import os
from typing import Optional, Dict, Any
from datetime import datetime

class DataLoader:
    """数据加载器"""
    
    def __init__(self, config_manager):
        self.config = config_manager
    
    def load_excel_file(self, filepath: str) -> Optional[pd.DataFrame]:
        """
        读取微信Excel账单文件
        
        参数:
            filepath: Excel文件路径
        
        返回:
            pandas DataFrame 或 None（如果读取失败）
        """
        print(f"📖 正在读取文件: {filepath}")
        
        try:
            # 尝试自动检测表头位置
            df = pd.read_excel(filepath, header=None, engine='openpyxl')
            
            # 查找数据开始行
            start_row = self._find_data_start_row(df)
            
            if start_row is None:
                print("❌ 无法找到数据开始行")
                return None
            
            # 重新读取，从找到的表头开始
            df = pd.read_excel(filepath, skiprows=start_row, engine='openpyxl')
            df.columns = [str(col).strip() for col in df.columns]
            
            # 预处理数据
            df = self._preprocess_data(df)
            
            print(f"✅ 成功读取 {len(df)} 条交易记录")
            return df
            
        # 在data_loader.py中，load_excel_file方法可以添加更具体的异常处理
        except FileNotFoundError:
            print(f"❌ 文件未找到: {filepath}")
            return None
        except pd.errors.EmptyDataError:
            print(f"❌ 文件为空: {filepath}")
            return None
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return None
    
    def _find_data_start_row(self, df: pd.DataFrame) -> Optional[int]:
        """查找数据开始行"""
        for i in range(min(20, len(df))):
            row_str = ' '.join(str(cell) for cell in df.iloc[i].astype(str))
            if '交易时间' in row_str and '交易类型' in row_str:
                return i
        return None
    
    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """预处理数据"""
        # 清理金额列
        if '金额(元)' in df.columns and '收/支' in df.columns:
            df['处理后的金额'] = df.apply(
                lambda row: self._clean_amount(row['金额(元)'], row['收/支']), 
                axis=1
            )
        
        # 确保必要的列存在
        required_columns = ['交易时间', '交易类型', '交易对方', '商品']
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''
        
        return df
    
    def _clean_amount(self, amount_str: Any, transaction_type: str) -> float:
        """清理金额字符串，支出为负数，收入为正数"""
        if pd.isna(amount_str):
            return 0.0
        
        amount_str = str(amount_str)
        amount_str = amount_str.replace('¥', '').replace(',', '').strip()
        
        try:
            amount = float(amount_str)
            
            if '支出' in str(transaction_type):
                return -abs(amount)
            elif '收入' in str(transaction_type):
                return abs(amount)
            else:
                return amount
            
        except (ValueError, TypeError):
            return 0.0
    
    def find_excel_files(self, directory: str = ".") -> list:
        """查找目录中的Excel账单文件"""
        excel_files = []
        
        for file in os.listdir(directory):
            if file.endswith(('.xlsx', '.xls')) and ('微信' in file or '账单' in file):
                excel_files.append(file)
        
        return excel_files