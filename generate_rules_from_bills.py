"""
generate_rules_from_bills.py - 从已分类账单生成规则脚本
从CSV文件中读取已分类的账单，生成分类规则并追加到规则文件
"""

import pandas as pd
import json
import os
import sys
import re
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple


def process_product(product_str: str) -> str:
    """
    处理商品名称
    
    规则：
    - "/" → ""（空字符串）
    - 纯数字 → ""（空字符串）
    - 文字+末尾数字（订单编号）→ 只保留文字部分，去掉末尾的数字
    
    参数:
        product_str: 原始商品字符串
        
    返回:
        处理后的商品字符串
    """
    if not product_str or pd.isna(product_str):
        return ""
    
    product_str = str(product_str).strip()
    
    # 1. 单个斜杠 "/" → 空字符串
    if product_str == "/":
        return ""
    
    # 2. 纯数字 → 空字符串
    if product_str.isdigit():
        return ""
    
    # 3. 文字+末尾数字（订单编号）→ 只保留文字部分
    # 使用正则表达式：匹配末尾是连续数字的情况（前面必须有非数字字符）
    # 例如："收钱码收款123" → "收钱码收款"
    # 但不匹配："123abc" 或 "abc123def"
    match = re.search(r'^(.+?)[\s]*(\d+)$', product_str)
    if match:
        text_part = match.group(1).rstrip()
        # 确保文字部分存在且不是纯数字
        if text_part and not text_part.isdigit():
            return text_part
    
    # 如果没有匹配到末尾数字模式，返回原字符串
    return product_str


def generate_rules_from_csv(csv_path: str) -> Tuple[Dict[str, Dict[str, int]], Dict[str, int]]:
    """
    从CSV文件生成规则字典
    
    参数:
        csv_path: CSV文件路径
        
    返回:
        (规则字典, 统计信息)
        规则字典格式: {规则键: {分类: 使用次数}} - 支持一个规则键对应多个分类
        统计信息: {'total_records': 总记录数, 'generated_rules': 生成的规则数}
    """
    print(f"正在读取CSV文件: {csv_path}")
    
    # 读取CSV文件
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
    except UnicodeDecodeError:
        # 如果UTF-8失败，尝试其他编码
        try:
            df = pd.read_csv(csv_path, encoding='gbk')
        except:
            df = pd.read_csv(csv_path, encoding='gb2312')
    
    # 检查必需的列
    required_columns = ['Original_Merchant', 'Original_Product', 'Category']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"CSV文件缺少必需的列: {', '.join(missing_columns)}")
    
    # 用于统计每个规则键的分类出现次数
    rule_category_count = defaultdict(lambda: defaultdict(int))
    
    total_records = 0
    valid_records = 0
    
    print("正在处理账单记录...")
    for idx, row in df.iterrows():
        total_records += 1
        
        # 获取数据
        merchant = str(row['Original_Merchant']).strip() if pd.notna(row['Original_Merchant']) else ""
        product_raw = row['Original_Product']
        category = str(row['Category']).strip() if pd.notna(row['Category']) else ""
        
        # 跳过无效数据
        if not merchant or not category:
            continue
        
        # 处理商品名称
        product = process_product(product_raw)
        
        # 构建规则键
        if product:
            rule_key = f"{merchant}|{product}"
        else:
            rule_key = f"{merchant}|"
        
        # 统计分类出现次数
        rule_category_count[rule_key][category] += 1
        valid_records += 1
        
        # 显示进度
        if (idx + 1) % 100 == 0:
            print(f"  已处理 {idx + 1}/{len(df)} 条记录...")
    
    print(f"  处理完成，共处理 {valid_records}/{total_records} 条有效记录")
    
    # 生成规则字典（新格式：支持多分类）
    # 格式: {规则键: {分类: 使用次数}}
    rules = {}
    for rule_key, category_counts in rule_category_count.items():
        # 直接使用分类字典，保留所有分类
        rules[rule_key] = dict(category_counts)
    
    stats = {
        'total_records': total_records,
        'valid_records': valid_records,
        'generated_rules': len(rules)
    }
    
    return rules, stats


def merge_rules(existing_rules: Dict[str, Dict[str, int]], new_rules: Dict[str, Dict[str, int]]) -> Tuple[Dict[str, Dict[str, int]], Dict[str, int]]:
    """
    将新规则合并到现有规则中（支持多分类格式）
    
    参数:
        existing_rules: 现有规则字典，格式: {规则键: {分类: 使用次数}}
        new_rules: 新生成的规则字典，格式: {规则键: {分类: 使用次数}}
        
    返回:
        (合并后的规则字典, 合并统计信息)
        合并统计: {'new_keys': 新增规则键数, 'new_categories': 新增分类数, 'updated_categories': 更新分类次数}
    """
    merged_rules = existing_rules.copy()
    stats = {'new_keys': 0, 'new_categories': 0, 'updated_categories': 0}
    
    for rule_key, new_categories in new_rules.items():
        # new_categories 是字典: {分类: 使用次数}
        if rule_key not in merged_rules:
            # 新规则键，直接添加
            merged_rules[rule_key] = new_categories.copy()
            stats['new_keys'] += 1
            stats['new_categories'] += len(new_categories)
        else:
            # 规则键已存在，合并分类字典
            existing_categories = merged_rules[rule_key]
            
            for category, count in new_categories.items():
                if category in existing_categories:
                    # 分类已存在，累加使用次数
                    existing_categories[category] += count
                    stats['updated_categories'] += 1
                else:
                    # 分类不存在，添加新分类
                    existing_categories[category] = count
                    stats['new_categories'] += 1
    
    return merged_rules, stats


def load_existing_rules(rules_file: str) -> Dict[str, Dict[str, int]]:
    """
    加载现有的规则文件（新格式：{规则键: {分类: 使用次数}}）
    
    参数:
        rules_file: 规则文件路径
        
    返回:
        规则字典，格式: {规则键: {分类: 使用次数}}
    """
    if not os.path.exists(rules_file):
        print(f"规则文件不存在，将创建新文件: {rules_file}")
        return {}
    
    try:
        with open(rules_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            rules = data.get('rules', {})
            
            # 验证格式（确保是新格式，不支持旧格式）
            for rule_key, rule_value in rules.items():
                if not isinstance(rule_value, dict):
                    raise ValueError(
                        f"规则文件包含旧格式规则: \"{rule_key}\"。"
                        f"新格式要求: {{\"分类\": 使用次数}}，"
                        f"但发现: {rule_value}。"
                        f"请重新生成规则文件。"
                    )
            
            print(f"已加载现有规则文件: {rules_file} ({len(rules)} 条规则键)")
            return rules
    except ValueError as e:
        print(f"❌ {e}")
        raise
    except Exception as e:
        print(f"⚠️  加载规则文件失败: {e}")
        return {}


def save_rules(rules: Dict, rules_file: str, metadata: Dict = None) -> None:
    """
    保存规则到JSON文件
    
    参数:
        rules: 规则字典
        rules_file: 规则文件路径
        metadata: 元数据（可选）
    """
    # 加载现有文件的metadata（如果存在）
    existing_metadata = None
    if os.path.exists(rules_file):
        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_metadata = existing_data.get('metadata', {})
                manual_edited = existing_data.get('manual_edited_rules', [])
        except:
            pass
    
    # 使用提供的metadata或现有的metadata
    if metadata is None:
        metadata = existing_metadata if existing_metadata else {}
    
    # 构建保存的数据结构
    rules_data = {
        'version': '2.0',
        'save_time': datetime.now().isoformat(),
        'total_rules': len(rules),
        'rules': rules,
        'metadata': metadata
    }
    
    # 保留manual_edited_rules（如果存在）
    if existing_metadata or (os.path.exists(rules_file)):
        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if 'manual_edited_rules' in existing_data:
                    rules_data['manual_edited_rules'] = existing_data['manual_edited_rules']
        except:
            pass
    
    # 保存文件
    try:
        with open(rules_file, 'w', encoding='utf-8') as f:
            json.dump(rules_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 规则已保存到: {rules_file} ({len(rules)} 条规则)")
    except Exception as e:
        print(f"❌ 保存规则失败: {e}")
        raise


def main():
    """主函数"""
    print("=" * 70)
    print("从已分类账单生成规则脚本")
    print("=" * 70)
    print()
    
    # 获取CSV文件路径
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = input("请输入CSV文件路径: ").strip().strip('"').strip("'")
    
    # 检查文件是否存在
    if not os.path.exists(csv_path):
        print(f"❌ 文件不存在: {csv_path}")
        sys.exit(1)
    
    # 确定规则文件路径（与CSV文件在同一目录）
    rules_file = os.path.join(os.path.dirname(os.path.abspath(csv_path)), 'bill_rules_optimized.json')
    if not os.path.exists(rules_file):
        # 如果当前目录没有，尝试脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        rules_file = os.path.join(script_dir, 'bill_rules_optimized.json')
    
    print(f"规则文件路径: {rules_file}")
    print()
    
    try:
        # 1. 从CSV生成规则
        new_rules, gen_stats = generate_rules_from_csv(csv_path)
        print()
        
        if not new_rules:
            print("⚠️  未生成任何规则，请检查CSV文件内容")
            return
        
        print(f"生成统计:")
        print(f"  总记录数: {gen_stats['total_records']}")
        print(f"  有效记录数: {gen_stats['valid_records']}")
        print(f"  生成的规则数: {gen_stats['generated_rules']}")
        print()
        
        # 2. 加载现有规则
        existing_rules = load_existing_rules(rules_file)
        print()
        
        # 3. 合并规则
        print("正在合并规则...")
        merged_rules, merge_stats = merge_rules(existing_rules, new_rules)
        print()
        
        print(f"合并统计:")
        print(f"  新增规则键: {merge_stats['new_keys']}")
        print(f"  新增分类到现有规则键: {merge_stats['new_categories']}")
        print(f"  更新分类（累加次数）: {merge_stats['updated_categories']}")
        print(f"  规则总数: {len(merged_rules)}")
        print()
        
        # 显示规则格式示例
        if merged_rules:
            example_key = list(merged_rules.keys())[0]
            example_value = merged_rules[example_key]
            print("规则格式示例:")
            print(f'  "{example_key}": {json.dumps(example_value, ensure_ascii=False, indent=4)}')
            print()
        
        # 4. 保存规则
        save_rules(merged_rules, rules_file)
        print()
        
        print("=" * 70)
        print("✅ 处理完成！")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

