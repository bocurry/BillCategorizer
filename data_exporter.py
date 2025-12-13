"""
data_exporter.py - 数据导出模块
负责数据格式转换和导出
"""

import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List

class DataExporter:
    """数据导出器"""
    
    def __init__(self, config_manager):
        self.config = config_manager
    
    def prepare_final_dataframe(self, df: pd.DataFrame, bill_source: str, 
                               default_person: str) -> pd.DataFrame:
        """准备最终输出数据"""
        final_df = pd.DataFrame()
        
        # 1. Name（商户 + 商品）
        final_df['Name'] = df.apply(
            lambda row: f"{row['交易对方']} - {row['商品']}" 
            if str(row['商品']) not in ['/', '无', 'nan', 'None'] and str(row['商品']).strip()
            else str(row['交易对方']), 
            axis=1
        )
        
        # 2. Category
        if '分类' in df.columns:
            final_df['Category'] = df['分类']
        
        # 3. Amount（确保支出为负，收入为正）
        if '处理后的金额' in df.columns:
            final_df['Amount'] = df['处理后的金额'].apply(lambda x: float(x) if pd.notna(x) else 0.0)
        elif '金额(元)' in df.columns and '收/支' in df.columns:
            # 如果没有处理后的金额，重新计算
            final_df['Amount'] = df.apply(
                lambda row: self._clean_amount(row['金额(元)'], row['收/支']), 
                axis=1
            )
        else:
            final_df['Amount'] = 0.0
        
        # 4. Date - 只保留日期部分，去掉时间
        if '交易时间' in df.columns:
            df['交易时间'] = pd.to_datetime(df['交易时间'], errors='coerce')
            final_df['Date'] = df['交易时间'].dt.strftime('%Y-%m-%d')
            
            # 排序（按日期降序）
            final_df = final_df.sort_values('Date', ascending=False)
        
        # 5. Person
        if '人员' in df.columns:
            final_df['Person'] = df['人员']
        else:
            final_df['Person'] = default_person
        
        # 6. Source
        final_df['Source'] = bill_source
        
        # 可选：保留原始信息（英文列名）
        final_df['Original_Merchant'] = df['交易对方']
        final_df['Original_Product'] = df['商品']
        final_df['Transaction_Type'] = df['交易类型'] if '交易类型' in df.columns else ''
        
        # 确保列顺序：Name, Category, Amount, Date, Person, Source
        main_columns = ['Name', 'Category', 'Amount', 'Date', 'Person', 'Source']
        extra_columns = [col for col in final_df.columns if col not in main_columns]
        
        final_df = final_df[main_columns + extra_columns]
        
        return final_df
    
    def _clean_amount(self, amount_str, transaction_type):
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
            
        except:
            return 0.0
    
    def export_to_csv(self, df: pd.DataFrame, bill_source: str) -> str:
        """导出数据到CSV文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"家庭账单_{bill_source}_{timestamp}.csv"
        
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ 账单已保存到: {output_file}")
        
        return output_file
    
    def display_preview(self, df: pd.DataFrame, preview_count: int = 5):
        """显示数据预览"""
        print(f"\n📋 数据预览（前{preview_count}条）:")
        print("="*70)
        print(f"{'Name':<30} {'Category':<10} {'Amount':>10} {'Date':<12} {'Person':<8} {'Source':<6}")
        print("-" * 70)
        
        preview_count = min(preview_count, len(df))
        for i in range(preview_count):
            row = df.iloc[i]
            name_display = str(row['Name'])[:28] + ('...' if len(str(row['Name'])) > 28 else '')
            amount_display = f"¥{row['Amount']:+.2f}"
            print(f"{name_display:<30} {str(row['Category']):<10} {amount_display:>10} {row['Date']:<12} {str(row['Person']):<8} {str(row['Source']):<6}")