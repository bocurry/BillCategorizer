"""
bill_analyzer.py - 通用年度收支分析脚本
分析CSV格式的账单数据，生成年度、月度、季度的收支统计报告和图表
支持自动检测CSV文件中的年份并生成对应年份的报告
"""

import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
import os
import re
from typing import Dict, Tuple, Optional
import warnings

# 设置matplotlib支持中文
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 忽略pandas警告
warnings.filterwarnings('ignore')


class BillAnalyzer:
    """通用年度收支分析器"""
    
    def __init__(self):
        self.df = None
        self.income_df = None
        self.expense_df = None
        self.year = None
        self.output_dir = os.path.dirname(os.path.abspath(__file__))
    
    def select_file(self) -> Optional[str]:
        """使用GUI选择CSV文件"""
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        
        filepath = filedialog.askopenfilename(
            title="选择账单CSV文件",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        
        root.destroy()
        return filepath if filepath else None
    
    def _parse_chinese_date(self, date_str: str) -> Optional[str]:
        """
        解析多种日期格式，转换为标准格式 'YYYY-MM-DD'
        支持的格式：
        - 中文格式：'2025年1月1日', '2025年01月01日'
        - 标准格式：'2025-01-01', '2025/01/01', '2025.01.01'
        - 带时间格式：'2025-01-01 12:00:00', '2025年1月1日 12:00:00'
        - Excel日期数字（如果传入的是数字）
        """
        if pd.isna(date_str):
            return None
        
        # 如果是数字（可能是Excel日期序列号），尝试转换
        if isinstance(date_str, (int, float)):
            try:
                # Excel日期从1900-01-01开始计算
                date_obj = pd.Timestamp('1900-01-01') + pd.Timedelta(days=int(date_str) - 2)
                return date_obj.strftime('%Y-%m-%d')
            except:
                return None
        
        # 转换为字符串处理
        date_str = str(date_str).strip()
        if not date_str or date_str.lower() in ['nan', 'none', '']:
            return None
        
        # 1. 尝试中文日期格式：YYYY年M月D日 或 YYYY年MM月DD日（可能带时间）
        match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
        if match:
            year, month, day = match.groups()
            try:
                # 验证日期有效性
                date_obj = pd.Timestamp(int(year), int(month), int(day))
                return date_obj.strftime('%Y-%m-%d')
            except:
                return None
        
        # 2. 尝试标准日期格式：YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD（可能带时间）
        patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # 2025-01-01
            r'(\d{4})/(\d{1,2})/(\d{1,2})',  # 2025/01/01
            r'(\d{4})\.(\d{1,2})\.(\d{1,2})',  # 2025.01.01
        ]
        
        for pattern in patterns:
            match = re.match(pattern, date_str)
            if match:
                year, month, day = match.groups()
                try:
                    date_obj = pd.Timestamp(int(year), int(month), int(day))
                    return date_obj.strftime('%Y-%m-%d')
                except:
                    continue
        
        # 3. 尝试使用pandas的to_datetime（最灵活，支持多种格式）
        try:
            date_obj = pd.to_datetime(date_str, errors='coerce')
            if pd.notna(date_obj):
                return date_obj.strftime('%Y-%m-%d')
        except:
            pass
        
        # 所有方法都失败，返回None
        return None
    
    def _detect_year(self, df: pd.DataFrame) -> Optional[int]:
        """从Date列中检测年份"""
        # 过滤掉无效的日期
        valid_dates = df['Date'].dropna()
        if len(valid_dates) == 0:
            return None
        
        # 提取年份并统计频率
        years = valid_dates.dt.year.value_counts()
        if len(years) == 0:
            return None
        
        # 返回最频繁出现的年份
        # 如果有多个年份但数据量相近，选择数据量最大的
        most_common_year = years.index[0]
        return int(most_common_year)
    
    def load_data(self, filepath: str) -> bool:
        """加载CSV文件并预处理数据"""
        try:
            # 尝试不同的编码
            encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(filepath, encoding=encoding)
                    print(f"✅ 使用 {encoding} 编码成功读取文件")
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            if df is None:
                raise ValueError("无法读取文件，尝试了所有编码方式")
            
            # 检查必需的列
            required_columns = ['Amount', 'Category', 'Date']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"CSV文件缺少必需的列: {', '.join(missing_columns)}")
            
            # 转换日期列 - 支持多种日期格式
            # 尝试解析各种日期格式
            original_date_count = len(df)
            df['Date'] = df['Date'].apply(self._parse_chinese_date)
            
            # 统计日期解析失败的数量
            failed_parse_count = df['Date'].isna().sum()
            if failed_parse_count > 0:
                print(f"⚠️  警告：有 {failed_parse_count} 条记录的日期解析失败（共 {original_date_count} 条）")
            
            # 转换解析后的日期字符串为datetime
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            
            # 检测年份
            self.year = self._detect_year(df)
            if self.year is None:
                raise ValueError("无法从文件中检测到有效年份，请检查Date列格式")
            
            # 筛选指定年份的数据
            df = df[df['Date'].dt.year == self.year].copy()
            
            if len(df) == 0:
                raise ValueError(f"文件中没有{self.year}年的数据")
            
            print(f"📅 检测到年份：{self.year}年，筛选后剩余 {len(df)} 条记录")
            
            # 确保Amount是数值类型 - 处理货币符号和逗号
            # 移除货币符号和逗号，然后转换为数值
            df['Amount'] = df['Amount'].astype(str).str.replace('¥', '', regex=False).str.replace(',', '', regex=False).str.strip()
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
            df = df.dropna(subset=['Amount', 'Date', 'Category'])
            
            # 分离收入和支出
            self.df = df
            self.income_df = df[df['Amount'] > 0].copy()
            self.expense_df = df[df['Amount'] < 0].copy()
            self.expense_df['Amount'] = self.expense_df['Amount'].abs()  # 支出转为正数
            
            print(f"✅ 数据加载成功：共 {len(df)} 条记录")
            print(f"   - 收入：{len(self.income_df)} 条")
            print(f"   - 支出：{len(self.expense_df)} 条")
            
            return True
            
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            return False
    
    def calculate_statistics(self) -> Dict:
        """计算统计分析数据"""
        stats = {
            'yearly': {},
            'monthly': {},
            'quarterly': {}
        }
        
        # 年度统计
        if len(self.income_df) > 0:
            income_by_category = self.income_df.groupby('Category')['Amount'].sum().sort_values(ascending=False)
            total_income = income_by_category.sum()
            stats['yearly']['income'] = {
                'by_category': income_by_category.to_dict(),
                'total': total_income,
                'count': len(self.income_df)
            }
        else:
            stats['yearly']['income'] = {'by_category': {}, 'total': 0, 'count': 0}
        
        if len(self.expense_df) > 0:
            expense_by_category = self.expense_df.groupby('Category')['Amount'].sum().sort_values(ascending=False)
            total_expense = expense_by_category.sum()
            stats['yearly']['expense'] = {
                'by_category': expense_by_category.to_dict(),
                'total': total_expense,
                'count': len(self.expense_df)
            }
        else:
            stats['yearly']['expense'] = {'by_category': {}, 'total': 0, 'count': 0}
        
        # 月度统计
        self.income_df['Month'] = self.income_df['Date'].dt.month
        self.expense_df['Month'] = self.expense_df['Date'].dt.month
        
        stats['monthly']['income'] = {}
        stats['monthly']['expense'] = {}
        
        for month in range(1, 13):
            month_income = self.income_df[self.income_df['Month'] == month]
            month_expense = self.expense_df[self.expense_df['Month'] == month]
            
            if len(month_income) > 0:
                income_by_cat = month_income.groupby('Category')['Amount'].sum().sort_values(ascending=False)
                stats['monthly']['income'][month] = {
                    'by_category': income_by_cat.to_dict(),
                    'total': income_by_cat.sum(),
                    'count': len(month_income)
                }
            else:
                stats['monthly']['income'][month] = {'by_category': {}, 'total': 0, 'count': 0}
            
            if len(month_expense) > 0:
                expense_by_cat = month_expense.groupby('Category')['Amount'].sum().sort_values(ascending=False)
                stats['monthly']['expense'][month] = {
                    'by_category': expense_by_cat.to_dict(),
                    'total': expense_by_cat.sum(),
                    'count': len(month_expense)
                }
            else:
                stats['monthly']['expense'][month] = {'by_category': {}, 'total': 0, 'count': 0}
        
        # 季度统计
        self.income_df['Quarter'] = self.income_df['Date'].dt.quarter
        self.expense_df['Quarter'] = self.expense_df['Date'].dt.quarter
        
        stats['quarterly']['income'] = {}
        stats['quarterly']['expense'] = {}
        
        for quarter in range(1, 5):
            q_income = self.income_df[self.income_df['Quarter'] == quarter]
            q_expense = self.expense_df[self.expense_df['Quarter'] == quarter]
            
            if len(q_income) > 0:
                income_by_cat = q_income.groupby('Category')['Amount'].sum().sort_values(ascending=False)
                stats['quarterly']['income'][quarter] = {
                    'by_category': income_by_cat.to_dict(),
                    'total': income_by_cat.sum(),
                    'count': len(q_income)
                }
            else:
                stats['quarterly']['income'][quarter] = {'by_category': {}, 'total': 0, 'count': 0}
            
            if len(q_expense) > 0:
                expense_by_cat = q_expense.groupby('Category')['Amount'].sum().sort_values(ascending=False)
                stats['quarterly']['expense'][quarter] = {
                    'by_category': expense_by_cat.to_dict(),
                    'total': expense_by_cat.sum(),
                    'count': len(q_expense)
                }
            else:
                stats['quarterly']['expense'][quarter] = {'by_category': {}, 'total': 0, 'count': 0}
        
        return stats
    
    def format_currency(self, amount: float) -> str:
        """格式化金额显示"""
        return f"¥{amount:,.2f}"
    
    def format_percentage(self, value: float, total: float) -> str:
        """格式化百分比显示"""
        if total == 0:
            return "0.00%"
        return f"{value / total * 100:.2f}%"
    
    def print_text_report(self, stats: Dict):
        """打印文本报告到控制台"""
        print("\n" + "="*70)
        print(f"=== {self.year}年度收支分析报告 ===")
        print("="*70)
        
        # 年度汇总
        print("\n【年度汇总】")
        print("-"*70)
        
        income_data = stats['yearly']['income']
        expense_data = stats['yearly']['expense']
        
        print(f"\n总收入：{self.format_currency(income_data['total'])} (共 {income_data['count']} 笔)")
        if income_data['by_category']:
            for category, amount in income_data['by_category'].items():
                percentage = self.format_percentage(amount, income_data['total'])
                print(f"  - {category}：{self.format_currency(amount)} ({percentage})")
        
        print(f"\n总支出：{self.format_currency(expense_data['total'])} (共 {expense_data['count']} 笔)")
        if expense_data['by_category']:
            for category, amount in expense_data['by_category'].items():
                percentage = self.format_percentage(amount, expense_data['total'])
                print(f"  - {category}：{self.format_currency(amount)} ({percentage})")
        
        net = income_data['total'] - expense_data['total']
        print(f"\n净收支：{self.format_currency(net)}")
        
        # 月度统计
        print("\n\n【月度统计】")
        print("-"*70)
        month_names = ['', '1月', '2月', '3月', '4月', '5月', '6月', 
                       '7月', '8月', '9月', '10月', '11月', '12月']
        
        for month in range(1, 13):
            month_income = stats['monthly']['income'][month]
            month_expense = stats['monthly']['expense'][month]
            
            if month_income['total'] > 0 or month_expense['total'] > 0:
                print(f"\n{month_names[month]}：")
                if month_income['total'] > 0:
                    print(f"  收入：{self.format_currency(month_income['total'])} (共 {month_income['count']} 笔)")
                    for category, amount in list(month_income['by_category'].items())[:5]:  # 只显示前5个
                        percentage = self.format_percentage(amount, month_income['total'])
                        print(f"    - {category}：{self.format_currency(amount)} ({percentage})")
                
                if month_expense['total'] > 0:
                    print(f"  支出：{self.format_currency(month_expense['total'])} (共 {month_expense['count']} 笔)")
                    for category, amount in list(month_expense['by_category'].items())[:5]:  # 只显示前5个
                        percentage = self.format_percentage(amount, month_expense['total'])
                        print(f"    - {category}：{self.format_currency(amount)} ({percentage})")
        
        # 季度统计
        print("\n\n【季度统计】")
        print("-"*70)
        quarter_names = {1: 'Q1 (1-3月)', 2: 'Q2 (4-6月)', 3: 'Q3 (7-9月)', 4: 'Q4 (10-12月)'}
        
        for quarter in range(1, 5):
            q_income = stats['quarterly']['income'][quarter]
            q_expense = stats['quarterly']['expense'][quarter]
            
            if q_income['total'] > 0 or q_expense['total'] > 0:
                print(f"\n{quarter_names[quarter]}：")
                if q_income['total'] > 0:
                    print(f"  收入：{self.format_currency(q_income['total'])} (共 {q_income['count']} 笔)")
                    for category, amount in q_income['by_category'].items():
                        percentage = self.format_percentage(amount, q_income['total'])
                        print(f"    - {category}：{self.format_currency(amount)} ({percentage})")
                
                if q_expense['total'] > 0:
                    print(f"  支出：{self.format_currency(q_expense['total'])} (共 {q_expense['count']} 笔)")
                    for category, amount in q_expense['by_category'].items():
                        percentage = self.format_percentage(amount, q_expense['total'])
                        print(f"    - {category}：{self.format_currency(amount)} ({percentage})")
        
        print("\n" + "="*70)
    
    def generate_csv_reports(self, stats: Dict):
        """生成CSV报告文件"""
        # 收入分析CSV
        income_rows = []
        income_rows.append(['统计维度', '分类', '金额', '比例', '笔数'])
        
        # 年度收入
        income_data = stats['yearly']['income']
        total_income = income_data['total']
        for category, amount in income_data['by_category'].items():
            percentage = amount / total_income * 100 if total_income > 0 else 0
            income_rows.append(['年度总计', category, amount, f"{percentage:.2f}%", income_data['count']])
        
        # 月度收入
        month_names = ['', '1月', '2月', '3月', '4月', '5月', '6月', 
                       '7月', '8月', '9月', '10月', '11月', '12月']
        for month in range(1, 13):
            month_data = stats['monthly']['income'][month]
            if month_data['total'] > 0:
                for category, amount in month_data['by_category'].items():
                    percentage = amount / month_data['total'] * 100 if month_data['total'] > 0 else 0
                    income_rows.append([month_names[month], category, amount, f"{percentage:.2f}%", month_data['count']])
        
        # 季度收入
        quarter_names = {1: 'Q1', 2: 'Q2', 3: 'Q3', 4: 'Q4'}
        for quarter in range(1, 5):
            q_data = stats['quarterly']['income'][quarter]
            if q_data['total'] > 0:
                for category, amount in q_data['by_category'].items():
                    percentage = amount / q_data['total'] * 100 if q_data['total'] > 0 else 0
                    income_rows.append([quarter_names[quarter], category, amount, f"{percentage:.2f}%", q_data['count']])
        
        income_df = pd.DataFrame(income_rows[1:], columns=income_rows[0])
        income_file = os.path.join(self.output_dir, f'{self.year}年度收入分析.csv')
        income_df.to_csv(income_file, index=False, encoding='utf-8-sig')
        print(f"✅ 收入分析报告已保存：{income_file}")
        
        # 支出分析CSV
        expense_rows = []
        expense_rows.append(['统计维度', '分类', '金额', '比例', '笔数'])
        
        # 年度支出
        expense_data = stats['yearly']['expense']
        total_expense = expense_data['total']
        for category, amount in expense_data['by_category'].items():
            percentage = amount / total_expense * 100 if total_expense > 0 else 0
            expense_rows.append(['年度总计', category, amount, f"{percentage:.2f}%", expense_data['count']])
        
        # 月度支出
        for month in range(1, 13):
            month_data = stats['monthly']['expense'][month]
            if month_data['total'] > 0:
                for category, amount in month_data['by_category'].items():
                    percentage = amount / month_data['total'] * 100 if month_data['total'] > 0 else 0
                    expense_rows.append([month_names[month], category, amount, f"{percentage:.2f}%", month_data['count']])
        
        # 季度支出
        for quarter in range(1, 5):
            q_data = stats['quarterly']['expense'][quarter]
            if q_data['total'] > 0:
                for category, amount in q_data['by_category'].items():
                    percentage = amount / q_data['total'] * 100 if q_data['total'] > 0 else 0
                    expense_rows.append([quarter_names[quarter], category, amount, f"{percentage:.2f}%", q_data['count']])
        
        expense_df = pd.DataFrame(expense_rows[1:], columns=expense_rows[0])
        expense_file = os.path.join(self.output_dir, f'{self.year}年度支出分析.csv')
        expense_df.to_csv(expense_file, index=False, encoding='utf-8-sig')
        print(f"✅ 支出分析报告已保存：{expense_file}")
        
        # 收支汇总CSV
        summary_rows = []
        summary_rows.append(['统计维度', '总收入', '总支出', '净收支', '收入笔数', '支出笔数'])
        
        # 年度汇总
        summary_rows.append([
            '年度总计',
            income_data['total'],
            expense_data['total'],
            income_data['total'] - expense_data['total'],
            income_data['count'],
            expense_data['count']
        ])
        
        # 月度汇总
        for month in range(1, 13):
            m_income = stats['monthly']['income'][month]
            m_expense = stats['monthly']['expense'][month]
            if m_income['total'] > 0 or m_expense['total'] > 0:
                summary_rows.append([
                    month_names[month],
                    m_income['total'],
                    m_expense['total'],
                    m_income['total'] - m_expense['total'],
                    m_income['count'],
                    m_expense['count']
                ])
        
        # 季度汇总
        for quarter in range(1, 5):
            q_income = stats['quarterly']['income'][quarter]
            q_expense = stats['quarterly']['expense'][quarter]
            if q_income['total'] > 0 or q_expense['total'] > 0:
                summary_rows.append([
                    quarter_names[quarter],
                    q_income['total'],
                    q_expense['total'],
                    q_income['total'] - q_expense['total'],
                    q_income['count'],
                    q_expense['count']
                ])
        
        summary_df = pd.DataFrame(summary_rows[1:], columns=summary_rows[0])
        summary_file = os.path.join(self.output_dir, f'{self.year}年度收支汇总.csv')
        summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
        print(f"✅ 收支汇总报告已保存：{summary_file}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除不能用于文件名的特殊字符"""
        # Windows 文件名不能包含的字符: < > : " / \ | ? *
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
    
    def generate_category_detail_csvs(self):
        """为每个收入和支出类别生成独立的CSV文件，包含该类别下的所有原始交易记录"""
        # 创建分类明细子文件夹
        category_dir = os.path.join(self.output_dir, '分类明细')
        os.makedirs(category_dir, exist_ok=True)
        
        # 获取所有收入类别（从income_df获取类别列表，但从df中筛选以保留原始Amount值）
        if len(self.income_df) > 0:
            income_categories = self.income_df['Category'].unique()
            for category in income_categories:
                # 从原始数据中筛选该类别的收入数据（Amount > 0）
                category_data = self.df[(self.df['Category'] == category) & (self.df['Amount'] > 0)].copy()
                
                if len(category_data) > 0:
                    # 清理类别名称，确保可以用于文件名
                    safe_category = self._sanitize_filename(str(category))
                    filename = f'收入-{safe_category}.csv'
                    filepath = os.path.join(category_dir, filename)
                    
                    # 保存CSV文件，保留所有原始列和原始Amount值
                    category_data.to_csv(filepath, index=False, encoding='utf-8-sig')
                    print(f"✅ 收入分类明细已保存：{filepath} (共 {len(category_data)} 条记录)")
        
        # 获取所有支出类别（从expense_df获取类别列表，但从df中筛选以保留原始Amount值）
        if len(self.expense_df) > 0:
            expense_categories = self.expense_df['Category'].unique()
            for category in expense_categories:
                # 从原始数据中筛选该类别的支出数据（Amount < 0）
                category_data = self.df[(self.df['Category'] == category) & (self.df['Amount'] < 0)].copy()
                
                if len(category_data) > 0:
                    # 清理类别名称，确保可以用于文件名
                    safe_category = self._sanitize_filename(str(category))
                    filename = f'支出-{safe_category}.csv'
                    filepath = os.path.join(category_dir, filename)
                    
                    # 保存CSV文件，保留所有原始列和原始Amount值
                    category_data.to_csv(filepath, index=False, encoding='utf-8-sig')
                    print(f"✅ 支出分类明细已保存：{filepath} (共 {len(category_data)} 条记录)")
        
        print(f"✅ 所有分类明细CSV文件已保存到：{category_dir}")
    
    def generate_charts(self, stats: Dict):
        """生成图表"""
        # 饼图 - 年度收入分类比例
        if stats['yearly']['income']['by_category']:
            fig, ax = plt.subplots(figsize=(10, 8))
            categories = list(stats['yearly']['income']['by_category'].keys())
            amounts = list(stats['yearly']['income']['by_category'].values())
            ax.pie(amounts, labels=categories, autopct='%1.2f%%', startangle=90)
            ax.set_title(f'{self.year}年度收入分类比例', fontsize=16, fontweight='bold')
            plt.tight_layout()
            income_pie_file = os.path.join(self.output_dir, f'{self.year}年度收入分类比例.png')
            plt.savefig(income_pie_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ 收入饼图已保存：{income_pie_file}")
        
        # 饼图 - 年度支出分类比例
        if stats['yearly']['expense']['by_category']:
            fig, ax = plt.subplots(figsize=(10, 8))
            categories = list(stats['yearly']['expense']['by_category'].keys())
            amounts = list(stats['yearly']['expense']['by_category'].values())
            ax.pie(amounts, labels=categories, autopct='%1.2f%%', startangle=90)
            ax.set_title(f'{self.year}年度支出分类比例', fontsize=16, fontweight='bold')
            plt.tight_layout()
            expense_pie_file = os.path.join(self.output_dir, f'{self.year}年度支出分类比例.png')
            plt.savefig(expense_pie_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ 支出饼图已保存：{expense_pie_file}")
        
        # 柱状图 - 年度收入分类金额
        if stats['yearly']['income']['by_category']:
            fig, ax = plt.subplots(figsize=(12, 6))
            categories = list(stats['yearly']['income']['by_category'].keys())
            amounts = list(stats['yearly']['income']['by_category'].values())
            bars = ax.bar(categories, amounts, color='#4CAF50')
            ax.set_title(f'{self.year}年度收入分类金额', fontsize=16, fontweight='bold')
            ax.set_xlabel('分类', fontsize=12)
            ax.set_ylabel('金额 (元)', fontsize=12)
            ax.tick_params(axis='x', rotation=45)
            # 添加数值标签
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:,.0f}',
                       ha='center', va='bottom')
            plt.tight_layout()
            income_bar_file = os.path.join(self.output_dir, f'{self.year}年度收入分类金额.png')
            plt.savefig(income_bar_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ 收入柱状图已保存：{income_bar_file}")
        
        # 柱状图 - 年度支出分类金额
        if stats['yearly']['expense']['by_category']:
            fig, ax = plt.subplots(figsize=(12, 6))
            categories = list(stats['yearly']['expense']['by_category'].keys())
            amounts = list(stats['yearly']['expense']['by_category'].values())
            bars = ax.bar(categories, amounts, color='#F44336')
            ax.set_title(f'{self.year}年度支出分类金额', fontsize=16, fontweight='bold')
            ax.set_xlabel('分类', fontsize=12)
            ax.set_ylabel('金额 (元)', fontsize=12)
            ax.tick_params(axis='x', rotation=45)
            # 添加数值标签
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:,.0f}',
                       ha='center', va='bottom')
            plt.tight_layout()
            expense_bar_file = os.path.join(self.output_dir, f'{self.year}年度支出分类金额.png')
            plt.savefig(expense_bar_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ 支出柱状图已保存：{expense_bar_file}")
        
        # 柱状图 - 月度收支对比
        months = list(range(1, 13))
        month_names_short = ['1月', '2月', '3月', '4月', '5月', '6月', 
                             '7月', '8月', '9月', '10月', '11月', '12月']
        monthly_income = [stats['monthly']['income'][m]['total'] for m in months]
        monthly_expense = [stats['monthly']['expense'][m]['total'] for m in months]
        
        fig, ax = plt.subplots(figsize=(14, 6))
        x = range(len(months))
        width = 0.35
        bars1 = ax.bar([i - width/2 for i in x], monthly_income, width, label='收入', color='#4CAF50')
        bars2 = ax.bar([i + width/2 for i in x], monthly_expense, width, label='支出', color='#F44336')
        ax.set_title(f'{self.year}年度月度收支对比', fontsize=16, fontweight='bold')
        ax.set_xlabel('月份', fontsize=12)
        ax.set_ylabel('金额 (元)', fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(month_names_short)
        ax.legend()
        plt.tight_layout()
        monthly_comparison_file = os.path.join(self.output_dir, f'{self.year}年度月度收支对比.png')
        plt.savefig(monthly_comparison_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ 月度收支对比图已保存：{monthly_comparison_file}")
        
        # 柱状图 - 季度收支对比
        quarters = [1, 2, 3, 4]
        quarter_names = ['Q1', 'Q2', 'Q3', 'Q4']
        quarterly_income = [stats['quarterly']['income'][q]['total'] for q in quarters]
        quarterly_expense = [stats['quarterly']['expense'][q]['total'] for q in quarters]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        x = range(len(quarters))
        width = 0.35
        bars1 = ax.bar([i - width/2 for i in x], quarterly_income, width, label='收入', color='#4CAF50')
        bars2 = ax.bar([i + width/2 for i in x], quarterly_expense, width, label='支出', color='#F44336')
        ax.set_title(f'{self.year}年度季度收支对比', fontsize=16, fontweight='bold')
        ax.set_xlabel('季度', fontsize=12)
        ax.set_ylabel('金额 (元)', fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(quarter_names)
        ax.legend()
        plt.tight_layout()
        quarterly_comparison_file = os.path.join(self.output_dir, f'{self.year}年度季度收支对比.png')
        plt.savefig(quarterly_comparison_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ 季度收支对比图已保存：{quarterly_comparison_file}")
        
        # 趋势图 - 月度收入趋势（按分类）
        if stats['yearly']['income']['by_category']:
            # 获取所有分类
            all_categories = list(stats['yearly']['income']['by_category'].keys())
            # 只显示前5个分类，避免图表过于复杂
            top_categories = all_categories[:5]
            
            fig, ax = plt.subplots(figsize=(14, 6))
            month_names_plot = ['1月', '2月', '3月', '4月', '5月', '6月', 
                               '7月', '8月', '9月', '10月', '11月', '12月']
            for category in top_categories:
                monthly_amounts = []
                for month in range(1, 13):
                    amount = stats['monthly']['income'][month]['by_category'].get(category, 0)
                    monthly_amounts.append(amount)
                ax.plot(month_names_plot, monthly_amounts, marker='o', label=category, linewidth=2)
            
            ax.set_title(f'{self.year}年度月度收入趋势（按分类）', fontsize=16, fontweight='bold')
            ax.set_xlabel('月份', fontsize=12)
            ax.set_ylabel('金额 (元)', fontsize=12)
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            income_trend_file = os.path.join(self.output_dir, f'{self.year}年度月度收入趋势.png')
            plt.savefig(income_trend_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ 收入趋势图已保存：{income_trend_file}")
        
        # 趋势图 - 月度支出趋势（按分类）
        if stats['yearly']['expense']['by_category']:
            # 获取所有分类
            all_categories = list(stats['yearly']['expense']['by_category'].keys())
            # 只显示前5个分类，避免图表过于复杂
            top_categories = all_categories[:5]
            
            fig, ax = plt.subplots(figsize=(14, 6))
            month_names_plot = ['1月', '2月', '3月', '4月', '5月', '6月', 
                               '7月', '8月', '9月', '10月', '11月', '12月']
            for category in top_categories:
                monthly_amounts = []
                for month in range(1, 13):
                    amount = stats['monthly']['expense'][month]['by_category'].get(category, 0)
                    monthly_amounts.append(amount)
                ax.plot(month_names_plot, monthly_amounts, marker='o', label=category, linewidth=2)
            
            ax.set_title(f'{self.year}年度月度支出趋势（按分类）', fontsize=16, fontweight='bold')
            ax.set_xlabel('月份', fontsize=12)
            ax.set_ylabel('金额 (元)', fontsize=12)
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            expense_trend_file = os.path.join(self.output_dir, f'{self.year}年度月度支出趋势.png')
            plt.savefig(expense_trend_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ 支出趋势图已保存：{expense_trend_file}")


def main():
    """主函数"""
    print("="*70)
    print("年度收支分析工具")
    print("="*70)
    
    analyzer = BillAnalyzer()
    
    # 选择文件
    filepath = analyzer.select_file()
    if not filepath:
        print("❌ 未选择文件，程序退出")
        return
    
    print(f"\n📁 已选择文件：{filepath}")
    
    # 加载数据
    if not analyzer.load_data(filepath):
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("错误", "数据加载失败，请检查文件格式")
        root.destroy()
        return
    
    # 计算统计
    print("\n📊 正在计算统计数据...")
    stats = analyzer.calculate_statistics()
    
    # 生成文本报告
    print("\n📄 生成文本报告...")
    analyzer.print_text_report(stats)
    
    # 生成CSV报告
    print("\n📋 生成CSV报告...")
    analyzer.generate_csv_reports(stats)
    
    # 生成分类明细CSV
    print("\n📁 生成分类明细CSV文件...")
    analyzer.generate_category_detail_csvs()
    
    # 生成图表
    print("\n📈 生成图表...")
    analyzer.generate_charts(stats)
    
    # 完成提示
    print("\n" + "="*70)
    print("✅ 分析完成！所有报告和图表已保存到当前目录")
    print("="*70)
    
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("完成", "分析完成！\n所有报告和图表已保存到当前目录。")
    root.destroy()


if __name__ == "__main__":
    main()

