"""
categorizer.py - 分类引擎主模块
协调各个模块完成分类任务
"""

import pandas as pd
from datetime import datetime
from collections import defaultdict
from typing import Tuple, Optional, Dict, List

class BillCategorizer:
    """账单分类器 - 主控制器"""
    
    def __init__(self, config_manager, data_loader, learning_engine, user_interface, data_exporter,
                 merge_master: bool = False):
        self.config = config_manager
        self.data_loader = data_loader
        self.learning_engine = learning_engine
        self.ui = user_interface
        self.exporter = data_exporter
        self.merge_master = merge_master

        from master_spreadsheet import MasterSpreadsheetMerger
        self.master_merger = MasterSpreadsheetMerger(config_manager)
        
        # 处理状态
        self.stats = defaultdict(int)
        self.current_bill_source = ""
        self.current_person = ""
    
    def _reset_gui_for_next_bill(self):
        """重置 GUI 状态以处理下一个账单。"""
        if hasattr(self.ui, 'run_on_main_thread'):
            self.ui.run_on_main_thread(self._reset_gui_for_next_bill_impl)
        else:
            self._reset_gui_for_next_bill_impl()

    def _reset_gui_for_next_bill_impl(self):
        """在主线程重置 GUI 组件状态。"""
        if hasattr(self.ui, 'reset_bill_processing_state'):
            self.ui.reset_bill_processing_state()
        elif hasattr(self.ui, 'classified_data'):
            self.ui.classified_data = []
            self.ui.tree_item_to_index = {}
        if hasattr(self.ui, 'result_window') and self.ui.result_window:
            try:
                if self.ui.result_window.winfo_exists():
                    self.ui.result_window.destroy()
            except Exception:
                pass
            self.ui.result_window = None
    
    def run(self):
        """主运行函数 - 支持批处理多个账单"""
        # 只在第一次运行时显示欢迎信息
        first_run = True
        
        while True:
            # 检查停止标志
            if hasattr(self.ui, 'should_stop') and self.ui.should_stop:
                break
            
            if first_run:
                if not hasattr(self.ui, 'show_results'):
                    self.ui.display_welcome()
                first_run = False
            else:
                # 重置统计信息，准备处理下一个账单
                self.stats = defaultdict(int)
                if hasattr(self.ui, 'show_results'):
                    self._reset_gui_for_next_bill()
            
            # 检查停止标志
            if hasattr(self.ui, 'should_stop') and self.ui.should_stop:
                break
            
            # 1. 选择账单来源
            self.current_bill_source = self.ui.select_bill_source()
            if not self.current_bill_source:
                if hasattr(self.ui, 'show_results'):
                    if not self.ui.ask_continue_processing():
                        break
                else:
                    if not self.ui.ask_continue_processing():
                        break
                continue
            
            # 检查停止标志
            if hasattr(self.ui, 'should_stop') and self.ui.should_stop:
                break
            
            # 2. 选择文件
            excel_files = self.data_loader.find_excel_files()
            selected_file = self.ui.display_file_list(excel_files)
            
            # 检查停止标志
            if hasattr(self.ui, 'should_stop') and self.ui.should_stop:
                break
            
            if not selected_file:
                # 用户取消选择文件，询问是否继续
                if not hasattr(self.ui, 'show_results'):
                    if not self.ui.ask_continue_processing():
                        break
                else:
                    # GUI模式：如果用户取消选择文件，询问是否继续
                    if not self.ui.ask_continue_processing():
                        break
                continue

            self.current_bill_source = self.data_loader.resolve_bill_source(
                selected_file, self.current_bill_source
            )
            
            # 检查停止标志
            if hasattr(self.ui, 'should_stop') and self.ui.should_stop:
                break
            
            # 3. 读取数据（根据用户选择的账单来源）
            df = self.data_loader.load_excel_file(selected_file, self.current_bill_source)
            if df is None:
                # 读取失败，询问是否继续
                if not hasattr(self.ui, 'show_results'):
                    print("❌ 读取文件失败")
                    if not self.ui.ask_continue_processing():
                        break
                else:
                    self.ui.show_error("读取文件失败")
                    if not self.ui.ask_continue_processing():
                        break
                continue
            
            # 检查停止标志
            if hasattr(self.ui, 'should_stop') and self.ui.should_stop:
                break
            
            # 4. 选择人员模式
            person_mode_result = self.ui.select_person_mode()
            
            # 检查停止标志
            if hasattr(self.ui, 'should_stop') and self.ui.should_stop:
                break
            
            if person_mode_result[1] == 'fixed':
                self.current_person = person_mode_result[0]
                person_mode = 'fixed'
            else:
                person_mode = 'per_transaction'
            
            # 5. 处理数据
            df = self._process_transactions(df, person_mode)
            
            # 检查停止标志
            if hasattr(self.ui, 'should_stop') and self.ui.should_stop:
                break
            
            # 检查是否有处理的数据
            if len(df) == 0:
                # 用户提前退出，没有处理任何数据
                is_gui = hasattr(self.ui, 'show_results')
                if is_gui:
                    self.ui.show_info("已取消处理，未保存任何数据")
                    # 关闭交易窗口
                    if hasattr(self.ui, '_destroy_transaction_window'):
                        if hasattr(self.ui, 'run_on_main_thread'):
                            self.ui.run_on_main_thread(self.ui._destroy_transaction_window)
                        else:
                            self.ui._destroy_transaction_window()
                    elif hasattr(self.ui, 'transaction_window') and self.ui.transaction_window:
                        try:
                            if hasattr(self.ui, 'run_on_main_thread'):
                                self.ui.run_on_main_thread(
                                    lambda: self.ui.transaction_window.destroy()
                                    if self.ui.transaction_window and self.ui.transaction_window.winfo_exists()
                                    else None
                                )
                            else:
                                self.ui.transaction_window.destroy()
                        except Exception:
                            pass
                        self.ui.transaction_window = None
                else:
                    print("\n⚠️  已取消处理，未保存任何数据")
                
                # 询问是否继续处理下一个账单
                if not self.ui.ask_continue_processing():
                    break
                continue
            
            # 检查停止标志
            if hasattr(self.ui, 'should_stop') and self.ui.should_stop:
                break
            
            # 6. 保存学习数据
            self.learning_engine.save_data()
            
            # 7. 导出结果（输出格式统一）
            # 如果是在GUI模式且存在已修改的DataFrame（可能包含删除的记录），优先使用它
            export_df = df
            is_gui = hasattr(self.ui, 'show_results')
            if is_gui and hasattr(self.ui, 'current_processed_df') and self.ui.current_processed_df is not None:
                # 使用GUI中可能被编辑/删除过的DataFrame
                export_df = self.ui.current_processed_df
            
            final_df = self.exporter.prepare_final_dataframe(export_df, self.current_bill_source, self.current_person)
            output_file = self.exporter.export_to_csv(final_df, self.current_bill_source)
            merge_result = self._maybe_merge_to_master(final_df)
            
            # 8. 显示结果（GUI 模式在同一窗口询问是否继续）
            should_continue = self._display_results(final_df, output_file, merge_result)
            
            # 检查停止标志
            if hasattr(self.ui, 'should_stop') and self.ui.should_stop:
                break
            
            # 9. 询问是否继续处理下一个账单
            if should_continue is not None:
                if not should_continue:
                    break
            elif not self.ui.ask_continue_processing():
                break
        
        # 所有处理完成
        is_gui = hasattr(self.ui, 'show_results')
        if not is_gui:
            print("\n👋 感谢使用！程序已退出。")
    
    def _process_transactions(self, df: pd.DataFrame, person_mode: str) -> pd.DataFrame:
        """处理所有交易记录"""
        # 检查是否是GUI模式
        is_gui = hasattr(self.ui, 'show_results')
        
        # 清空之前的已分类数据
        if is_gui:
            if hasattr(self.ui, 'reset_bill_processing_state'):
                if hasattr(self.ui, 'run_on_main_thread'):
                    self.ui.run_on_main_thread(self.ui.reset_bill_processing_state)
                else:
                    self.ui.reset_bill_processing_state()
            elif hasattr(self.ui, 'classified_data'):
                self.ui.classified_data = []
                self.ui.tree_item_to_index = {}
        
        if not is_gui:
            print("\n🚀 开始分类处理...")
        
        categories = []
        persons = []
        is_auto_list = []  # 新增：记录是否自动分类
        
        for idx, row in df.iterrows():
            # 检查停止标志
            if hasattr(self.ui, 'should_stop') and self.ui.should_stop:
                # 如果用户关闭窗口，返回已处理的数据
                break
            
            self.stats['total'] += 1
            
            # 显示进度
            self.ui.display_progress(self.stats['total'], len(df))
            
            # 处理单条交易
            category, person, is_auto = self._process_single_transaction(
                idx + 1, len(df), row, person_mode
            )
            
            if category is None:  # 用户选择退出
                if not is_gui:
                    print("\n⚠️  用户中断处理")
                break
            
            categories.append(category)
            persons.append(person)
            is_auto_list.append(is_auto)  # 记录分类方式
            
            # GUI模式下，更新界面并添加到已分类列表
            if is_gui and hasattr(self.ui, 'root'):
                if is_auto and hasattr(self.ui, 'defer_classified_transaction'):
                    if hasattr(self.ui, 'run_on_main_thread'):
                        self.ui.run_on_main_thread(
                            self.ui.defer_classified_transaction,
                            row, category, person, is_auto, self.stats['total'], len(df),
                        )
                    else:
                        self.ui.defer_classified_transaction(
                            row, category, person, is_auto, self.stats['total'], len(df)
                        )
                elif hasattr(self.ui, 'add_classified_transaction'):
                    if hasattr(self.ui, 'flush_deferred_classified_transactions'):
                        if hasattr(self.ui, 'run_on_main_thread'):
                            self.ui.run_on_main_thread(self.ui.flush_deferred_classified_transactions)
                        else:
                            self.ui.flush_deferred_classified_transactions()
                    if hasattr(self.ui, 'run_on_main_thread'):
                        self.ui.run_on_main_thread(
                            self.ui.add_classified_transaction,
                            row, category, person, is_auto,
                        )
                    else:
                        self.ui.add_classified_transaction(row, category, person, is_auto)
        
        if is_gui and hasattr(self.ui, 'flush_deferred_classified_transactions'):
            if hasattr(self.ui, 'run_on_main_thread'):
                self.ui.run_on_main_thread(self.ui.flush_deferred_classified_transactions)
            else:
                self.ui.flush_deferred_classified_transactions()
        
        # 添加结果列（只添加已处理的记录）
        # 如果用户提前退出，categories和persons的长度可能小于df的长度
        if len(categories) > 0:
            # 创建新的DataFrame，只包含已处理的记录
            processed_df = df.iloc[:len(categories)].copy()
            processed_df['分类'] = categories
            processed_df['人员'] = persons
            processed_df['是否自动分类'] = is_auto_list  # 新增列
            
            # 新增：保存到 GUI（如果存在）
            if is_gui and hasattr(self.ui, 'current_processed_df'):
                # 如果 current_processed_df 已经存在且有数据，说明用户可能已经编辑过
                # 需要合并 processed_df 和 current_processed_df，保留编辑后的分类
                if self.ui.current_processed_df is not None and len(self.ui.current_processed_df) > 0:
                    # 合并策略：使用 processed_df 作为基础，但保留 current_processed_df 中编辑后的分类
                    if len(processed_df) == len(self.ui.current_processed_df):
                        # 如果长度相同，保留 current_processed_df 的分类和人员（用户编辑后的）
                        # 但更新其他列（如果有变化）
                        processed_df['分类'] = self.ui.current_processed_df['分类'].values
                        processed_df['人员'] = self.ui.current_processed_df['人员'].values
                        # 如果 current_processed_df 有是否自动分类列，也保留它
                        if '是否自动分类' in self.ui.current_processed_df.columns:
                            processed_df['是否自动分类'] = self.ui.current_processed_df['是否自动分类'].values
                        self.ui.current_processed_df = processed_df
                    elif len(processed_df) > len(self.ui.current_processed_df):
                        # 如果 processed_df 更长，说明有新的记录
                        # 保留 current_processed_df 中已有的记录的分类，新记录使用 processed_df 的分类
                        for idx in range(len(self.ui.current_processed_df)):
                            if idx < len(processed_df):
                                processed_df.iloc[idx, processed_df.columns.get_loc('分类')] = self.ui.current_processed_df.iloc[idx]['分类']
                                processed_df.iloc[idx, processed_df.columns.get_loc('人员')] = self.ui.current_processed_df.iloc[idx]['人员']
                                if '是否自动分类' in self.ui.current_processed_df.columns and '是否自动分类' in processed_df.columns:
                                    processed_df.iloc[idx, processed_df.columns.get_loc('是否自动分类')] = self.ui.current_processed_df.iloc[idx]['是否自动分类']
                        self.ui.current_processed_df = processed_df
                    else:
                        # 如果 current_processed_df 更长，说明用户可能删除了记录
                        # 使用 current_processed_df（保留用户的操作）
                        pass  # 不更新，保持 current_processed_df
                else:
                    # 如果 current_processed_df 为空，直接设置
                    self.ui.current_processed_df = processed_df
                # 新增：保存 categorizer 引用到 GUI
                if hasattr(self.ui, 'categorizer'):
                    self.ui.categorizer = self
            
            return processed_df
        else:
            # 如果没有处理任何记录，返回空的DataFrame
            if is_gui and hasattr(self.ui, 'current_processed_df'):
                self.ui.current_processed_df = None
            return df.iloc[0:0].copy()
    
    def _process_single_transaction(self, idx: int, total: int, row: dict, 
                                   person_mode: str) -> Tuple[Optional[str], Optional[str], bool]:
        """处理单条交易记录
        
        返回:
            (category, person, is_auto) - 分类、人员、是否自动分类
        """
        # 显示交易信息
        self.ui.display_transaction(idx, total, row)
        
        # 选择人员
        merchant = str(row.get('交易对方', '未知商户'))
        if person_mode == 'per_transaction':
            person = self.ui.select_person_for_transaction(merchant)
        else:
            person = self.current_person
        
        # 获取商品信息（data_loader已统一映射为"商品"字段）
        product = str(row.get('商品', ''))
        
        # 获取交易类型
        tx_type = str(row.get('交易类型', ''))

        # 获取分类建议（传入商品信息）
        suggestions = self.learning_engine.get_suggestions(merchant, product, tx_type)
        base_categories = self.config.get('categories.base_categories', [])
        
        # 检查是否精准匹配（自动分类）
        # 只有当建议数量为1且包含"精准匹配"标记时，才是真正的精准匹配
        exact_match = False
        exact_category = None
        if suggestions:
            if len(suggestions) == 1:
                category, reason = list(suggestions.items())[0]
                if "精准匹配" in reason:
                    exact_match = True
                    exact_category = category
        
        # 如果精准匹配，直接使用分类，跳过用户选择
        if exact_match and exact_category:
            category = exact_category
            is_auto = True  # 标记为自动分类
            self.stats['auto'] += 1
            
            # 记录学习
            amount = row.get('处理后的金额', row.get('金额(元)', 0))
            if isinstance(amount, (int, float)):
                self.learning_engine.learn_from_decision(
                    merchant, category, person, self.current_bill_source, amount, product
                )
            else:
                self.learning_engine.learn_from_decision(
                    merchant, category, person, self.current_bill_source, 0, product
                )
            
            return category, person, is_auto
        
        # 非精准匹配，显示分类菜单让用户选择
        is_auto = False  # 标记为手动分类
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
            return None, None, False
        elif choice == 's':
            self.stats['skipped'] += 1
            return '待确认', person, False
        elif choice == 'n':
            category = self.ui.get_validated_input(
                prompt="请输入新分类名称: ",
                input_type='text'
            )
            # 将新分类添加到基础分类列表
            if category and category not in base_categories:
                base_categories.append(category)
                # 更新配置
                self.config.set('categories.base_categories', base_categories)
                self.config.save_custom_config()
            self.stats['manual'] += 1
        elif isinstance(choice, int):
            if choice <= len(suggestions):
                category = list(suggestions.keys())[choice-1]
                # 如果选择了系统建议的分类，仍然算作自动分类（因为系统推荐了）
                # 但这不是精准匹配，所以 is_auto = False
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
                merchant, category, person, self.current_bill_source, amount, product
            )
        else:
            self.learning_engine.learn_from_decision(
                merchant, category, person, self.current_bill_source, 0, product
            )
        
        return category, person, is_auto
    
    def _should_merge_to_master(self) -> bool:
        if self.merge_master:
            return True
        if hasattr(self.ui, 'should_merge_to_master'):
            return bool(self.ui.should_merge_to_master())
        return self.master_merger.is_enabled()

    def _maybe_merge_to_master(self, final_df: pd.DataFrame):
        if not self._should_merge_to_master():
            return None

        is_gui = hasattr(self.ui, 'show_results')
        prompt = bool(self.config.get('master_spreadsheet.prompt_before_merge', True))
        if prompt and not is_gui and hasattr(self.ui, 'ask_merge_to_master'):
            if not self.ui.ask_merge_to_master():
                return None

        result = self.master_merger.merge_dataframe(final_df)
        if not result.success:
            if hasattr(self.ui, 'show_error'):
                self.ui.show_error(f'总表合并失败: {result.error}')
            else:
                print(f'❌ 总表合并失败: {result.error}')
        return result

    def _display_results(self, final_df: pd.DataFrame, output_file: str, merge_result=None):
        """显示处理结果。GUI 模式返回是否继续；CLI 模式返回 None。"""
        # 检查是否是GUI界面
        if hasattr(self.ui, 'show_results'):
            # GUI模式：使用GUI显示结果，并在结果窗口询问是否继续
            engine_stats = self.learning_engine.get_statistics()
            return self.ui.show_results(
                final_df, output_file, self.stats, engine_stats, merge_result
            )
        else:
            # CLI模式：使用命令行显示
            # 显示预览
            preview_count = self.config.get('display.preview_count', 5)
            self.exporter.display_preview(final_df, preview_count)
            
            # 显示统计
            self._display_statistics(final_df)
            
            print(f"\n💾 规则库状态:")
            engine_stats = self.learning_engine.get_statistics()
            print(f"  当前规则数: {engine_stats['total_rules']} / {engine_stats['max_rules']}")
            print(f"  历史记录数: {engine_stats['total_history']} / {engine_stats['max_history']}")

            if merge_result is not None:
                if merge_result.success:
                    print(f"\n📊 {merge_result.summary()}")
                else:
                    print(f"\n❌ {merge_result.summary()}")
        return None
    
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