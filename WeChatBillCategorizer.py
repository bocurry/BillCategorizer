"""
微信账单自动分类助手 - 优化版
包含：输入校验、账单来源、性能优化
"""

import pandas as pd
import json
import os
import sys
import pickle
import gzip
from datetime import datetime
from collections import defaultdict, OrderedDict

class OptimizedBillCategorizer:
    """优化版账单分类助手"""
    """
    微信账单自动分类助手 - 主控制器类
    
    核心功能：
    1. 读取微信导出的Excel账单
    2. 交互式分类交易记录
    3. 渐进式学习用户分类习惯
    4. 导出结构化数据到CSV
    
    设计模式：MVC（模型-视图-控制器）
    数据流：Excel → DataFrame → 分类处理 → CSV
    
    属性说明：
    - rules: 商户到分类的映射规则库 {商户: [分类, 使用次数]}
    - history: 分类决策历史记录
    - stats: 处理统计数据
    - merchant_index: 商户名前缀索引，加速模糊匹配
    """
    
    def __init__(self):
        # 配置文件路径
        self.rules_file = 'bill_rules_optimized.json' # 规则库文件
        self.history_file = 'bill_history.json'  # 历史记录文件
        
        # 最大数据量限制（防止性能问题）
        self.MAX_RULES = 50000  # 最多50000条规则
        self.MAX_HISTORY = 5000  # 最多5000条历史记录
        
        # 加载已有规则（优化加载）
        self.rules = self.load_rules_optimized()
        self.history = self.load_json_file(self.history_file, [], max_items=self.MAX_HISTORY)
    
        self.bill_sources = ["微信", "支付宝", "银行", "现金", "其他"]
        self.current_bill_source = "微信"
        
        # 人员选项
        self.people_options = ["男主人", "女主人", "家庭公用"]
        self.current_person = "家庭公用"
        
        # 分类系统
        self.base_categories = [
            "餐饮", "出行", "住房贷款", "购物", "生活缴费",
            "娱乐", "医疗", "学习", "人情往来", "汽车",
            "投资", "其他消费", "工资", "其他", "父母",
            "党费", "运动", "其他收入", "旅游", "服务", "公积金",
            "贷款", "山姆&盒马", "水果&超市", "买菜"
        ]
        
        # 特殊交易类型映射
        self.special_types = {
            '转账': '人情往来',
            '微信红包': '人情往来',
            '收付款': '人情往来',
        }
        
        # 快速查找索引
        self.merchant_index = self.build_merchant_index()
        
        # 统计数据
        self.stats = defaultdict(int)
    
    def load_rules_optimized(self):
        """优化加载规则"""
        # 先尝试加载JSON
        if os.path.exists(self.rules_file):
            try:
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    rules = data.get('rules', {})
                    
                    # 限制规则数量
                    if len(rules) > self.MAX_RULES:
                        print(f"⚠️  规则数量过多({len(rules)})，保留最常用的{self.MAX_RULES}条")
                        # 假设规则格式为 {商户: [分类, 使用次数]}
                        sorted_rules = sorted(rules.items(), 
                                            key=lambda x: x[1][1] if isinstance(x[1], list) and len(x[1]) > 1 else 0,
                                            reverse=True)
                        rules = dict(sorted_rules[:self.MAX_RULES])
                    
                    return rules
            except Exception as e:
                print(f"⚠️  加载规则失败: {e}")
        
        return {}
    
    def build_merchant_index(self):
        """构建商户名关键词索引"""
        index = defaultdict(list)
        for merchant in self.rules.keys():
            if isinstance(merchant, str) and len(merchant) > 1:
                # 提取前3个字符作为索引
                key = merchant[:3].lower()
                index[key].append(merchant)
        return index
    
    def load_json_file(self, filename, default=None, max_items=None):
        """加载JSON文件并限制数量"""
        if default is None:
            default = []
        
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if max_items and len(data) > max_items:
                        data = data[-max_items:]  # 保留最新的
                    return data
            except Exception as e:
                print(f"⚠️  警告：无法读取 {filename}: {e}")
                return default
        return default
    
    def save_data_optimized(self):
        """优化保存数据"""
        # 1. 保存规则（限制数量）
        if len(self.rules) > self.MAX_RULES:
            # 按使用次数排序，保留最常用的
            rules_list = list(self.rules.items())
            if all(isinstance(v, (list, tuple)) and len(v) > 1 for v in self.rules.values()):
                rules_list.sort(key=lambda x: x[1][1], reverse=True)
            self.rules = dict(rules_list[:self.MAX_RULES])
        
        rules_data = {
            'version': '2.0',
            'save_time': datetime.now().isoformat(),
            'total_rules': len(self.rules),
            'rules': self.rules,
            'metadata': {
                'bill_sources': self.bill_sources,
                'people_options': self.people_options,
                'base_categories': self.base_categories
            }
        }
        
        try:
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, ensure_ascii=False, separators=(',', ':'))
            print(f"✅ 规则已保存到: {self.rules_file} ({len(self.rules)}条)")
        except Exception as e:
            print(f"❌ 保存规则失败: {e}")
        
        # 2. 保存历史（限制数量）
        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[-self.MAX_HISTORY:]
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存历史失败: {e}")
    
    def get_validated_input(self, prompt, input_type='number', valid_range=None, valid_options=None):
        """获取并验证用户输入"""
        while True:
            try:
                user_input = input(prompt).strip()
                
                if input_type == 'number':
                    if not user_input.isdigit():
                        print("❌ 请输入数字")
                        continue
                    
                    num = int(user_input)
                    if valid_range:
                        min_val, max_val = valid_range
                        if min_val <= num <= max_val:
                            return num
                        else:
                            print(f"❌ 请输入 {min_val}-{max_val} 之间的数字")
                    else:
                        return num
                
                elif input_type == 'choice':
                    if valid_options:
                        if user_input in valid_options:
                            return user_input
                        else:
                            print(f"❌ 请输入以下选项之一: {', '.join(valid_options)}")
                    else:
                        return user_input
                
                elif input_type == 'text':
                    if not user_input:
                        print("❌ 输入不能为空")
                        continue
                    return user_input
                
                elif input_type == 'category_choice':
                    if user_input.lower() in ['q', 's', 'n']:
                        return user_input.lower()
                    elif user_input.isdigit():
                        num = int(user_input)
                        if valid_range and valid_range[0] <= num <= valid_range[1]:
                            return num
                        else:
                            print(f"❌ 请输入 {valid_range[0]}-{valid_range[1]} 或 q/s/n")
                    else:
                        # 自由输入分类名
                        if user_input.strip():
                            return user_input
                        else:
                            print("❌ 分类名称不能为空")
                
            except KeyboardInterrupt:
                print("\n⚠️  输入被中断")
                raise
            except Exception as e:
                print(f"❌ 输入错误: {e}")
    
    def select_bill_source(self):
        """选择账单来源（带校验）"""
        print("\n💳 请选择账单来源:")
        print("="*50)
        for i, source in enumerate(self.bill_sources, 1):
            print(f"  [{i}] {source}")
        
        choice = self.get_validated_input(
            prompt=f"\n请选择账单来源 (1-{len(self.bill_sources)}): ",
            input_type='number',
            valid_range=(1, len(self.bill_sources))
        )
        
        self.current_bill_source = self.bill_sources[choice-1]
        print(f"✅ 账单来源: {self.current_bill_source}")
    
    def select_person_mode(self):
        """选择人员模式（带校验）"""
        print("\n👥 请选择人员分配方式:")
        print("="*50)
        print("  [1] 所有记录统一人员")
        print("  [2] 每条记录单独选择")
        
        choice = self.get_validated_input(
            prompt="\n请选择 (1-2): ",
            input_type='number',
            valid_range=(1, 2)
        )
        
        if choice == 1:
            return self.select_unified_person()
        else:
            return 'per_transaction'
    
    def select_unified_person(self):
        """选择统一人员（带校验）"""
        print("\n👤 请选择统一人员:")
        for i, person in enumerate(self.people_options, 1):
            print(f"  [{i}] {person}")
        
        choice = self.get_validated_input(
            prompt=f"\n请选择人员 (1-{len(self.people_options)}): ",
            input_type='number',
            valid_range=(1, len(self.people_options))
        )
        
        self.current_person = self.people_options[choice-1]
        print(f"✅ 统一人员: {self.current_person}")
        return 'fixed'
    
    def select_person_for_transaction(self, merchant):
        """为单条交易选择人员（带校验）"""
        print(f"\n交易: {merchant}")
        print("请选择人员:")
        
        for i, person in enumerate(self.people_options, 1):
            print(f"  [{i}] {person}")
        
        choice = self.get_validated_input(
            prompt=f"\n请选择人员 (1-{len(self.people_options)}): ",
            input_type='number',
            valid_range=(1, len(self.people_options))
        )
        
        return self.people_options[choice-1]
    
    def clean_amount(self, amount_str, transaction_type):
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
    
    def read_wechat_excel(self, filepath):
        """读取微信Excel账单"""
        print(f"📖 正在读取文件: {filepath}")
        
        try:
            df = pd.read_excel(filepath, header=None, engine='openpyxl')
            
            # 查找数据开始行
            start_row = 0
            for i in range(min(20, len(df))):
                row_str = ' '.join(str(cell) for cell in df.iloc[i].astype(str))
                if '交易时间' in row_str and '交易类型' in row_str:
                    start_row = i
                    break
            
            # 重新读取
            df = pd.read_excel(filepath, skiprows=start_row, engine='openpyxl')
            df.columns = [str(col).strip() for col in df.columns]
            
            # 预处理金额
            if '金额(元)' in df.columns and '收/支' in df.columns:
                df['处理后的金额'] = df.apply(
                    lambda row: self.clean_amount(row['金额(元)'], row['收/支']), 
                    axis=1
                )
            
            print(f"✅ 成功读取 {len(df)} 条交易记录")
            return df
            
        except Exception as e:
            print(f"❌ 读取失败: {e}")
            return None
    
    def get_suggestions(self, merchant, product, transaction_type):
        """获取分类建议（优化查找）"""
        suggestions = {}
        merchant_str = str(merchant)
        
        # 1. 特殊交易类型
        for type_key, category in self.special_types.items():
            if type_key in transaction_type:
                suggestions[category] = f"交易类型: {type_key}"
                return suggestions  # 特殊类型优先
        
        # 2. 精确匹配
        if merchant_str in self.rules:
            if isinstance(self.rules[merchant_str], (list, tuple)):
                category = self.rules[merchant_str][0]
            else:
                category = self.rules[merchant_str]
            suggestions[category] = f"精确匹配: {merchant_str}"
        
        # 3. 模糊匹配（使用索引加速）
        if len(merchant_str) >= 3:
            index_key = merchant_str[:3].lower()
            similar_merchants = self.merchant_index.get(index_key, [])
            
            for similar_merchant in similar_merchants:
                if similar_merchant in merchant_str or merchant_str in similar_merchant:
                    if isinstance(self.rules[similar_merchant], (list, tuple)):
                        category = self.rules[similar_merchant][0]
                    else:
                        category = self.rules[similar_merchant]
                    suggestions[category] = f"类似商户: {similar_merchant}"
                    break
        
        return suggestions
    
    def process_transaction(self, idx, total, row, person_mode):
        """处理单条交易（带输入校验）"""
        merchant = str(row.get('交易对方', '未知商户'))
        product = str(row.get('商品', '无'))
        tx_type = str(row.get('交易类型', '未知类型'))
        amount = row.get('处理后的金额', row.get('金额(元)', 0))
        date = row.get('交易时间', '未知时间')
        
        # 显示交易信息
        print("\n" + "="*70)
        print(f"📝 交易 {idx}/{total}")
        print(f"🕐 时间: {date}")
        print(f"🏪 商户: {merchant}")
        print(f"📦 商品: {product}")
        
        if isinstance(amount, (int, float)):
            print(f"💰 金额: ¥{amount:+.2f} ({tx_type})")
        else:
            print(f"💰 金额: {amount} ({tx_type})")
        print("="*70)
        
        # 选择人员
        if person_mode == 'per_transaction':
            person = self.select_person_for_transaction(merchant)
        else:
            person = self.current_person
        
        # 检查特殊交易类型
        for type_key, category in self.special_types.items():
            if type_key in tx_type:
                print(f"✅ 自动分类为: {category} (交易类型: {type_key})")
                self.stats['auto'] += 1
                return category, person
        
        # 获取建议
        suggestions = self.get_suggestions(merchant, product, tx_type)
        
        # 显示分类选择
        if suggestions:
            print("\n🤖 系统建议:")
            suggestions_list = list(suggestions.items())
            for i, (category, reason) in enumerate(suggestions_list, 1):
                print(f"  [{i}] {category} ← {reason}")
        
        print("\n🎯 基础分类:")
        start_idx = len(suggestions) + 1
        for i, category in enumerate(self.base_categories, start_idx):
            print(f"  [{i}] {category}")
        
        print(f"  [n] 输入新分类")
        print(f"  [s] 跳过（标记为待确认）")
        print(f"  [q] 退出程序")
        
        # 获取用户选择（带校验）
        max_choice = start_idx + len(self.base_categories) - 1
        choice = self.get_validated_input(
            prompt=f"\n请选择分类 (1-{max_choice} 或 n/s/q): ",
            input_type='category_choice',
            valid_range=(1, max_choice)
        )
        
        if choice == 'q':
            return None, None
        elif choice == 's':
            self.stats['skipped'] += 1
            return '待确认', person
        elif choice == 'n':
            new_cat = self.get_validated_input(
                prompt="请输入新分类名称: ",
                input_type='text'
            )
            category = new_cat
            self.stats['manual'] += 1
        elif isinstance(choice, int):
            if choice <= len(suggestions):
                category = list(suggestions.keys())[choice-1]
                self.stats['auto'] += 1
            else:
                category = self.base_categories[choice - start_idx]
                self.stats['manual'] += 1
        else:
            category = choice
            self.stats['manual'] += 1
        
        # 更新规则（记录使用次数）
        if merchant not in self.rules:
            self.rules[merchant] = [category, 1]
            # 更新索引
            if len(merchant) >= 3:
                index_key = merchant[:3].lower()
                if index_key not in self.merchant_index:
                    self.merchant_index[index_key] = []
                self.merchant_index[index_key].append(merchant)
        else:
            if isinstance(self.rules[merchant], (list, tuple)):
                self.rules[merchant][1] += 1
            else:
                self.rules[merchant] = [self.rules[merchant], 2]
        
        # 记录历史
        self.history.append({
            'merchant': merchant,
            'category': category,
            'person': person,
            'bill_source': self.current_bill_source,
            'amount': amount if isinstance(amount, (int, float)) else 0,
            'timestamp': datetime.now().isoformat()
        })
        
        return category, person
    
    def prepare_final_dataframe(self, df):
        """准备最终输出数据"""
        # 确定金额列
        amount_col = '处理后的金额' if '处理后的金额' in df.columns else '金额(元)'
        
        # 构建最终DataFrame
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
        if amount_col in df.columns:
            final_df['Amount'] = df[amount_col].apply(lambda x: float(x) if pd.notna(x) else 0.0)
        elif '金额(元)' in df.columns and '收/支' in df.columns:
            final_df['Amount'] = df.apply(
                lambda row: self.clean_amount(row['金额(元)'], row['收/支']), 
                axis=1
            )
        else:
            final_df['Amount'] = 0.0
        
        # 4. Date - 只保留日期部分，去掉时间
        if '交易时间' in df.columns:
            # 先将日期字符串转换为datetime对象
            df['交易时间'] = pd.to_datetime(df['交易时间'], errors='coerce')
            
            # 提取日期部分，格式化为 YYYY-MM-DD
            final_df['Date'] = df['交易时间'].dt.strftime('%Y-%m-%d')
            
            # 排序（按日期降序）
            final_df = final_df.sort_values('Date', ascending=False)
        
        # 5. Person
        if '人员' in df.columns:
            final_df['Person'] = df['人员']
        else:
            final_df['Person'] = self.current_person
        
        # 6. Source
        final_df['Source'] = self.current_bill_source
        
        # 可选：保留原始信息（英文列名）
        final_df['Original_Merchant'] = df['交易对方']
        final_df['Original_Product'] = df['商品']
        final_df['Transaction_Type'] = df['交易类型'] if '交易类型' in df.columns else ''
        
        # 确保列顺序：Name, Category, Amount, Date, Person, Source
        main_columns = ['Name', 'Category', 'Amount', 'Date', 'Person', 'Source']
        extra_columns = [col for col in final_df.columns if col not in main_columns]
        
        final_df = final_df[main_columns + extra_columns]
        
        return final_df
    
    def run(self):
        """主运行函数"""
        print("🎯 账单自动分类助手 - 优化版")
        print("="*70)
        print("输出包含：Name, Category, Amount, Date, Person, Source")
        print("="*70)
        
        # 选择账单来源
        self.select_bill_source()
        
        # 查找文件
        excel_files = [f for f in os.listdir('.') 
                      if f.endswith(('.xlsx', '.xls')) and ('微信' in f or '账单' in f)]
        
        if not excel_files:
            print("❌ 未找到账单文件")
            input("按回车键退出...")
            return
        
        # 选择文件
        print("📁 找到以下文件:")
        for i, file in enumerate(excel_files, 1):
            print(f"  [{i}] {file}")
        
        choice = self.get_validated_input(
            prompt=f"\n请选择文件 (1-{len(excel_files)}): ",
            input_type='number',
            valid_range=(1, len(excel_files))
        )
        
        selected_file = excel_files[choice-1]
        
        # 读取数据
        df = self.read_wechat_excel(selected_file)
        if df is None:
            input("按回车键退出...")
            return
        
        # 选择人员模式
        person_mode = self.select_person_mode()
        
        # 处理数据
        print("\n🚀 开始分类处理...")
        categories = []
        persons = []
        
        for idx, row in df.iterrows():
            self.stats['total'] += 1
            
            if idx > 0 and idx % 10 == 0:
                print(f"⏳ 进度: {idx}/{len(df)} ({idx/len(df)*100:.1f}%)")
            
            category, person = self.process_transaction(idx+1, len(df), row, person_mode)
            
            if category is None:
                print("\n⚠️  用户中断处理")
                break
            
            categories.append(category)
            persons.append(person)
        
        # 添加结果列
        df['分类'] = categories[:len(df)]
        df['人员'] = persons[:len(df)]
        
        # 保存数据
        self.save_data_optimized()
        
        # 生成最终输出
        final_df = self.prepare_final_dataframe(df)
        
        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"家庭账单_{self.current_bill_source}_{timestamp}.csv"
        
        # 只保存主要列到CSV
        final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ 账单已保存到: {output_file}")
        
        # 显示预览
        print(f"\n📋 数据预览（前5条）:")
        print("="*70)
        print(f"{'Name':<30} {'Category':<10} {'Amount':>10} {'Date':<12} {'Person':<8} {'Source':<6}")
        print("-" * 70)
        
        preview_count = min(5, len(final_df))
        for i in range(preview_count):
            row = final_df.iloc[i]
            name_display = str(row['Name'])[:28] + ('...' if len(str(row['Name'])) > 28 else '')
            amount_display = f"¥{row['Amount']:+.2f}"
            print(f"{name_display:<30} {str(row['Category']):<10} {amount_display:>10} {row['Date']:<12} {str(row['Person']):<8} {str(row['Source']):<6}")
        
        # 显示统计
        self.show_statistics(final_df)
        
        input("\n✨ 处理完成！按回车键退出...")
    
    def show_statistics(self, df):
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
        
        print(f"\n💾 规则库状态:")
        print(f"  当前规则数: {len(self.rules)} / {self.MAX_RULES}")
        print(f"  历史记录数: {len(self.history)} / {self.MAX_HISTORY}")

def main():
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
        
        # 创建并运行分类器
        print("正在启动账单分类助手...")
        categorizer = OptimizedBillCategorizer()
        categorizer.run()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  程序被用户中断")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")

if __name__ == "__main__":
    main()