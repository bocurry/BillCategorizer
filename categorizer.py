"""
categorizer.py - 分类引擎主模块
协调各个模块完成分类任务
"""

import pandas as pd
from datetime import datetime
from collections import defaultdict
from typing import Tuple, Optional, Dict

class BillCategorizer:
    """账单分类器 - 主控制器"""
    
    def __init__(self, config_manager, data_loader, learning_engine, user_interface, data_exporter):
        self.config = config_manager
        self.data_loader = data_loader
        self.learning_engine = learning_engine
        self.ui = user_interface
        self.exporter = data_exporter
        
        # 处理状态
        self.stats = defaultdict(int)
        self.current_bill_source = ""
        self.current_person = ""
    
    def run(self):
        """主运行函数"""
        self.ui.display_welcome()
        
        # 1. 选择账单来源
        self.current_bill_source = self.ui.select_bill_source()
        
        # 2. 选择文件
        excel_files = self.data_loader.find_excel_files()
        selected_file = self.ui.display_file_list(excel_files)
        
        if not selected_file:
            input("按回车键退出...")
            return
        
        # 3. 读取数据
        df = self.data_loader.load_excel_file(selected_file)
        if df is None:
            input("按回车键退出...")
            return
        
        # 4. 选择人员模式
        person_mode_result = self.ui.select_person_mode()
        if person_mode_result[1] == 'fixed':
            self.current_person = person_mode_result[0]
            person_mode = 'fixed'
        else:
            person_mode = 'per_transaction'
        
        # 5. 处理数据
        df = self._process_transactions(df, person_mode)
        
        # 6. 保存学习数据
        self.learning_engine.save_data()
        
        # 7. 导出结果
        final_df = self.exporter.prepare_final_dataframe(df, self.current_bill_source, self.current_person)
        output_file = self.exporter.export_to_csv(final_df, self.current_bill_source)
        
        # 8. 显示结果
        self._display_results(final_df, output_file)
        
        input("\n✨ 处理完成！按回车键退出...")
    
    def _process_transactions(self, df: pd.DataFrame, person_mode: str) -> pd.DataFrame:
        """处理所有交易记录"""
        print("\n🚀 开始分类处理...")
        
        categories = []
        persons = []
        
        for idx, row in df.iterrows():
            self.stats['total'] += 1
            
            # 显示进度
            self.ui.display_progress(idx, len(df))
            
            # 处理单条交易
            category, person = self._process_single_transaction(
                idx + 1, len(df), row, person_mode
            )
            
            if category is None:  # 用户选择退出
                print("\n⚠️  用户中断处理")
                break
            
            categories.append(category)
            persons.append(person)
        
        # 添加结果列
        df['分类'] = categories[:len(df)]
        df['人员'] = persons[:len(df)]
        
        return df
    
    def _process_single_transaction(self, idx: int, total: int, row: dict, 
                                   person_mode: str) -> Tuple[Optional[str], Optional[str]]:
        """处理单条交易记录"""
        # 显示交易信息
        self.ui.display_transaction(idx, total, row)
        
        # 选择人员
        merchant = str(row.get('交易对方', '未知商户'))
        if person_mode == 'per_transaction':
            person = self.ui.select_person_for_transaction(merchant)
        else:
            person = self.current_person
        
        # 检查特殊交易类型
        tx_type = str(row.get('交易类型', ''))
        special_types = self.config.get('categories.special_types', {})
        for type_key, category in special_types.items():
            if type_key in tx_type:
                print(f"✅ 自动分类为: {category} (交易类型: {type_key})")
                self.stats['auto'] += 1
                
                # 记录学习
                amount = row.get('处理后的金额', row.get('金额(元)', 0))
                if isinstance(amount, (int, float)):
                    self.learning_engine.learn_from_decision(
                        merchant, category, person, self.current_bill_source, amount
                    )
                
                return category, person
        
        # 获取分类建议
        suggestions = self.learning_engine.get_suggestions(merchant, tx_type)
        base_categories = self.config.get('categories.base_categories', [])
        
        # 显示分类菜单
        self.ui.display_classification_menu(suggestions, base_categories)
        
        # 获取用户选择
        max_choice = len(suggestions) + len(base_categories)
        choice = self.ui.get_validated_input(
            prompt=f"\n请选择分类 (1-{max_choice} 或 n/s/q): ",
            input_type='category_choice',
            valid_range=(1, max_choice)
        )
        
        # 处理用户选择
        if choice == 'q':
            return None, None
        elif choice == 's':
            self.stats['skipped'] += 1
            return '待确认', person
        elif choice == 'n':
            category = self.ui.get_validated_input(
                prompt="请输入新分类名称: ",
                input_type='text'
            )
            self.stats['manual'] += 1
        elif isinstance(choice, int):
            if choice <= len(suggestions):
                category = list(suggestions.keys())[choice-1]
                self.stats['auto'] += 1
            else:
                category = base_categories[choice - len(suggestions) - 1]
                self.stats['manual'] += 1
        else:
            category = choice
            self.stats['manual'] += 1
        
        # 记录学习
        amount = row.get('处理后的金额', row.get('金额(元)', 0))
        if isinstance(amount, (int, float)):
            self.learning_engine.learn_from_decision(
                merchant, category, person, self.current_bill_source, amount
            )
        else:
            self.learning_engine.learn_from_decision(
                merchant, category, person, self.current_bill_source, 0
            )
        
        return category, person
    
    def _display_results(self, final_df: pd.DataFrame, output_file: str):
        """显示处理结果"""
        # 显示预览
        preview_count = self.config.get('display.preview_count', 5)
        self.exporter.display_preview(final_df, preview_count)
        
        # 显示统计
        self._display_statistics(final_df)
        
        print(f"\n💾 规则库状态:")
        engine_stats = self.learning_engine.get_statistics()
        print(f"  当前规则数: {engine_stats['total_rules']} / {engine_stats['max_rules']}")
        print(f"  历史记录数: {engine_stats['total_history']} / {engine_stats['max_history']}")
    
    def _display_statistics(self, df: pd.DataFrame):
        """显示统计信息"""
        print("\n" + "="*70)
        print("📊 处理统计")
        print("="*70)
        
        print(f"总记录数: {self.stats['total']}")
        print(f"自动分类: {self.stats.get('auto', 0)}")
        print(f"手动分类: {self.stats.get('manual', 0)}")
        print(f"跳过记录: {self.stats.get('skipped', 0)}")
        
        if 'Amount' in df.columns:
            total_income = df[df['Amount'] > 0]['Amount'].sum()
            total_expense = df[df['Amount'] < 0]['Amount'].sum()
            balance = df['Amount'].sum()
            
            print(f"\n💰 金额统计:")
            print(f"  总收入: ¥{total_income:+.2f}")
            print(f"  总支出: ¥{total_expense:+.2f}")
            print(f"  净余额: ¥{balance:+.2f}")
        
        # 按分类统计
        if 'Category' in df.columns and 'Amount' in df.columns:
            print(f"\n🏷️  按分类统计:")
            category_stats = df.groupby('Category').agg({
                'Amount': ['count', 'sum']
            })
            category_stats.columns = ['笔数', '总金额']
            
            for category, row in category_stats.iterrows():
                print(f"  {category}: {row['笔数']}笔, ¥{row['总金额']:+.2f}")
        
        # 按人员统计
        if 'Person' in df.columns and 'Amount' in df.columns:
            print(f"\n👥 按人员统计:")
            person_stats = df.groupby('Person').agg({
                'Amount': ['count', 'sum']
            })
            person_stats.columns = ['笔数', '总金额']
            
            for person, row in person_stats.iterrows():
                print(f"  {person}: {row['笔数']}笔, ¥{row['总金额']:+.2f}")