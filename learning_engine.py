"""
learning_engine.py - 学习引擎模块
负责规则库的管理、学习和查询
"""

import json
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

class LearningEngine:
    """学习引擎 - 管理分类规则和学习"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        
        # 规则库数据结构
        self.rules: Dict[str, List] = {}  # {商户: [分类, 使用次数]}
        self.history: List[Dict] = []
        
        # 性能限制
        limits = self.config.get_limits()
        self.max_rules = limits.get('max_rules', 50000)
        self.max_history = limits.get('max_history', 5000)
        
        # 索引加速
        self.merchant_index: Dict[str, List[str]] = defaultdict(list)
        
        # 加载已有数据
        self._load_data()
    
    def _load_data(self):
        """加载规则库和历史记录"""
        # 加载规则库
        rules_file = self.config.get_file_path('rules_file')
        self.rules = self._load_rules_with_limit(rules_file, self.max_rules)
        
        # 如果进行了迁移，保存迁移后的规则
        if hasattr(self, '_pending_migration_rules') and self._pending_migration_rules is not None:
            # 临时保存迁移后的规则
            temp_rules = self.rules
            self.rules = self._pending_migration_rules
            self.save_data()
            self.rules = temp_rules  # 恢复self.rules（可能被限制规则数量）
            self._pending_migration_rules = None  # 清除临时变量
        
        # 加载历史记录
        history_file = self.config.get_file_path('history_file')
        self.history = self._load_json_file(history_file, [], self.max_history)
        
        # 构建索引
        self._build_merchant_index()
    
    def _migrate_rules(self, rules: Dict) -> Tuple[Dict, bool]:
        """迁移规则库：清理规则键中商品部分的数字
        
        返回:
            (迁移后的规则字典, 是否进行了迁移)
        """
        migrated_rules = {}
        migration_needed = False
        
        for rule_key, rule_value in rules.items():
            # 检查是否需要迁移（规则键是否包含|分隔符，且商品部分可能包含数字）
            if '|' in rule_key:
                merchant_part, product_part = rule_key.split('|', 1)
                # 检查商品部分是否包含需要清理的内容（长数字串、日期时间等）
                if re.search(r'\d{7,}', product_part) or \
                   re.search(r'\d{4}-\d{1,2}-\d{1,2}', product_part) or \
                   re.search(r'\d{3}\*{4}\d{4}', product_part) or \
                   re.search(r'[川京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏琼宁使领][A-Z]\d{1}[A-Z0-9]{4,5}', product_part):
                    # 需要迁移：清理商品部分
                    cleaned_product = self._remove_numbers_from_product(product_part)
                    new_key = f"{merchant_part}|{cleaned_product}"
                    migration_needed = True
                else:
                    # 不需要迁移
                    new_key = rule_key
            else:
                # 旧格式规则（不包含|），不需要迁移
                new_key = rule_key
            
            # 合并相同规则键的统计
            if new_key in migrated_rules:
                # 合并统计信息
                old_value = migrated_rules[new_key]
                if isinstance(old_value, dict) and isinstance(rule_value, dict):
                    # 两个都是字典格式，合并分类统计
                    merged_dict = old_value.copy()
                    for category, count in rule_value.items():
                        if category in merged_dict:
                            merged_dict[category] += count
                        else:
                            merged_dict[category] = count
                    migrated_rules[new_key] = merged_dict
                elif isinstance(old_value, (list, tuple)) and isinstance(rule_value, (list, tuple)):
                    # 两个都是列表格式，如果分类相同则累加，否则转换为字典格式
                    old_category = old_value[0]
                    old_count = old_value[1] if len(old_value) > 1 else 1
                    new_category = rule_value[0]
                    new_count = rule_value[1] if len(rule_value) > 1 else 1
                    
                    if old_category == new_category:
                        migrated_rules[new_key] = [old_category, old_count + new_count]
                    else:
                        migrated_rules[new_key] = {old_category: old_count, new_category: new_count}
                else:
                    # 格式不一致，转换为字典格式
                    if isinstance(old_value, dict):
                        merged_dict = old_value.copy()
                        if isinstance(rule_value, (list, tuple)):
                            category = rule_value[0]
                            count = rule_value[1] if len(rule_value) > 1 else 1
                            merged_dict[category] = merged_dict.get(category, 0) + count
                        else:
                            merged_dict[rule_value] = merged_dict.get(rule_value, 0) + 1
                        migrated_rules[new_key] = merged_dict
                    elif isinstance(rule_value, dict):
                        merged_dict = rule_value.copy()
                        if isinstance(old_value, (list, tuple)):
                            category = old_value[0]
                            count = old_value[1] if len(old_value) > 1 else 1
                            merged_dict[category] = merged_dict.get(category, 0) + count
                        else:
                            merged_dict[old_value] = merged_dict.get(old_value, 0) + 1
                        migrated_rules[new_key] = merged_dict
                    else:
                        # 都是单个值
                        if old_value == rule_value:
                            # 相同分类，累加（转换为列表格式）
                            migrated_rules[new_key] = [old_value, 2]
                        else:
                            # 不同分类，转换为字典格式
                            migrated_rules[new_key] = {old_value: 1, rule_value: 1}
            else:
                # 新规则键，直接添加
                migrated_rules[new_key] = rule_value
        
        if migration_needed:
            print(f"✅ 规则库已迁移：清理了规则键中的数字（{len(rules)} → {len(migrated_rules)}条规则）")
        
        return migrated_rules, migration_needed
    
    def _load_rules_with_limit(self, filename: str, max_rules: int) -> Dict:
        """加载规则库并限制数量"""
        if not os.path.exists(filename):
            return {}
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                rules = data.get('rules', {})
                
                # 迁移规则库（清理规则键中的数字）
                rules, migration_needed = self._migrate_rules(rules)
                
                # 限制规则数量
                if len(rules) > max_rules:
                    print(f"⚠️  规则数量过多({len(rules)})，保留最常用的{max_rules}条")
                    
                    # 排序规则：按使用次数排序
                    def get_total_count(rule_value):
                        """获取规则的总使用次数"""
                        if isinstance(rule_value, dict):
                            # 字典格式：返回所有分类的使用次数之和
                            return sum(rule_value.values())
                        elif isinstance(rule_value, (list, tuple)) and len(rule_value) > 1:
                            # 列表格式：[分类, 次数]
                            return rule_value[1]
                        else:
                            # 单个值或其他格式
                            return 0
                    
                    sorted_rules = sorted(rules.items(), 
                                        key=lambda x: get_total_count(x[1]),
                                        reverse=True)
                    rules = dict(sorted_rules[:max_rules])
                
                # 如果进行了迁移，需要在加载后保存
                # 暂时存储到实例变量中，供_load_data使用
                if migration_needed:
                    self._pending_migration_rules = rules.copy()  # 保存迁移后且限制后的规则
                
                return rules
        except Exception as e:
            print(f"⚠️  加载规则失败: {e}")
            return {}
    
    def _load_json_file(self, filename: str, default, max_items: int = None):
        """加载JSON文件并限制数量"""
        if not os.path.exists(filename):
            return default
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if max_items and len(data) > max_items:
                    data = data[-max_items:]  # 保留最新的
                return data
        except Exception as e:
            print(f"⚠️  警告：无法读取 {filename}: {e}")
            return default
    
    def _remove_numbers_from_product(self, product_str: str) -> str:
        """去除商品字符串中的数字（订单号、时间、电话等）"""
        if not product_str:
            return product_str
        
        result = product_str
        
        # 1. 去除日期时间格式：2025-10-10、19:03:、2025-10-10 19:03:
        result = re.sub(r'\d{4}-\d{1,2}-\d{1,2}\s*\d{1,2}:\d{1,2}:?\d{0,2}', '', result)
        result = re.sub(r'\d{4}-\d{1,2}-\d{1,2}', '', result)
        result = re.sub(r'\d{1,2}:\d{1,2}:?\d{0,2}', '', result)
        
        # 2. 去除电话号码格式：173****9937等
        result = re.sub(r'\d{3}\*{4}\d{4}', '', result)
        
        # 3. 去除金额：300.0元、¥300.0等（需要在去除长数字串之前处理，因为金额可能包含数字）
        result = re.sub(r'[¥￥]?\d+\.?\d*\s*元', '', result)
        
        # 4. 去除车牌号：川A4EH19等（省份简称+字母+数字+字母数字组合）
        result = re.sub(r'[川京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏琼宁使领][A-Z]\d{1}[A-Z0-9]{4,5}', '', result)
        
        # 5. 去除长数字串（超过6位的连续数字，可能是订单号、手机号等）
        # 注意：这个要放在最后，因为它会匹配所有长数字串（包括11位手机号）
        result = re.sub(r'\d{7,}', '', result)
        
        # 6. 清理多余的下划线和空格
        result = re.sub(r'_+', '_', result)
        result = re.sub(r'\s+', ' ', result)
        result = result.strip('_').strip()
        
        return result
    
    def _build_merchant_index(self):
        """构建商户名关键词索引（支持组合键格式）"""
        self.merchant_index = defaultdict(list)
        for rule_key in self.rules.keys():
            if isinstance(rule_key, str) and len(rule_key) > 1:
                # 如果是组合键格式（包含|），提取商户名部分
                if '|' in rule_key:
                    merchant_part = rule_key.split('|')[0]
                else:
                    merchant_part = rule_key
                
                # 提取前3个字符作为索引
                if len(merchant_part) >= 3:
                    key = merchant_part[:3].lower()
                    self.merchant_index[key].append(rule_key)
    
    def get_suggestions(self, merchant: str, product: str = "", transaction_type: str = "") -> Dict[str, str]:
        """
        获取分类建议
        
        参数:
            merchant: 商户名
            product: 商品名（可选）
            transaction_type: 交易类型（可选，保持向后兼容）
        
        返回:
            建议字典 {分类: 理由}，如果精准匹配，理由包含"精准匹配"标记
        """
        suggestions = {}
        merchant_str = str(merchant).strip()
        product_str = str(product).strip() if product else ""
        
        # 处理空商品名或"无"
        if product_str in ["", "无", "/"]:
            product_str = ""
        else:
            # 去除数字（订单号、时间等）
            product_str = self._remove_numbers_from_product(product_str)
        
        # 1. 优先尝试组合键匹配（商户+商品 或 商户|）
        if product_str:
            combined_key = f"{merchant_str}|{product_str}"
        else:
            combined_key = f"{merchant_str}|"
        
        if combined_key in self.rules:
            rule_value = self.rules[combined_key]
            
            # 判断是字典格式（多分类或单分类字典）还是列表/单个值
            if isinstance(rule_value, dict):
                # 字典格式：可能是多分类或单分类
                categories = list(rule_value.keys())
                if len(categories) == 1:
                    # 单分类：标记为精准匹配（但商品为空时例外）
                    category = categories[0]
                    count = rule_value[category]
                    if product_str:  # 有商品时才是精准匹配
                        suggestions[category] = f"精准匹配: {combined_key} (使用{count}次)"
                    else:  # 商品为空，使用推荐匹配
                        suggestions[category] = f"推荐匹配: {combined_key} (使用{count}次)"
                    return suggestions
                else:
                    # 多分类：返回所有分类作为建议，不标记为精准匹配
                    for category, count in rule_value.items():
                        suggestions[category] = f"推荐匹配: {combined_key} (使用{count}次)"
                    return suggestions
            elif isinstance(rule_value, (list, tuple)):
                # 列表格式：[分类, 次数] - 单分类
                category = rule_value[0]
                count = rule_value[1] if len(rule_value) > 1 else 1
                if product_str:  # 有商品时才是精准匹配
                    suggestions[category] = f"精准匹配: {combined_key} (使用{count}次)"
                else:  # 商品为空，使用推荐匹配
                    suggestions[category] = f"推荐匹配: {combined_key} (使用{count}次)"
                return suggestions
            else:
                # 单个值（向后兼容旧格式）- 单分类
                category = rule_value
                if product_str:  # 有商品时才是精准匹配
                    suggestions[category] = f"精准匹配: {combined_key}"
                else:  # 商品为空，使用推荐匹配
                    suggestions[category] = f"推荐匹配: {combined_key}"
                return suggestions
        
        # 2. 模糊匹配（使用索引加速，仅用于旧规则格式）
        if len(merchant_str) >= 3:
            index_key = merchant_str[:3].lower()
            similar_keys = self.merchant_index.get(index_key, [])
            
            for similar_key in similar_keys:
                # 只处理旧格式规则（不包含|的）
                if '|' not in similar_key:
                    if similar_key in merchant_str or merchant_str in similar_key:
                        rule_value = self.rules[similar_key]
                        if isinstance(rule_value, (list, tuple)):
                            category = rule_value[0]
                        elif isinstance(rule_value, dict):
                            # 如果是字典，取第一个分类（使用次数最多的）
                            category = max(rule_value.items(), key=lambda x: x[1])[0]
                        else:
                            category = rule_value
                        suggestions[category] = f"类似商户: {similar_key}"
                        break
        
        return suggestions
    
    def learn_from_decision(self, merchant: str, category: str, 
                           person: str, bill_source: str, amount: float,
                           product: str = "", update_existing: bool = False, old_category: str = None):
        """
        从用户决策中学习
        
        参数:
            merchant: 商户名
            category: 用户选择的分类
            person: 人员
            bill_source: 账单来源
            amount: 金额
            product: 商品名（可选）
            update_existing: 是否更新已存在的记录（用于修改分类时）
            old_category: 旧的分类（用于查找要更新的记录）
        """
        merchant_str = str(merchant).strip()
        product_str = str(product).strip() if product else ""
        
        # 处理空商品名或"无"
        if product_str in ["", "无", "/"]:
            product_str = ""
        else:
            # 去除数字（订单号、时间等），确保规则库中存储的是清理后的格式
            product_str = self._remove_numbers_from_product(product_str)
        
        # 构建组合键
        if product_str:
            rule_key = f"{merchant_str}|{product_str}"
        else:
            rule_key = f"{merchant_str}|"
        
        # 更新规则库（使用组合键，支持多分类）
        if rule_key not in self.rules:
            # 新规则：使用字典格式存储（支持多分类）
            self.rules[rule_key] = {category: 1}
            # 更新索引
            if len(merchant_str) >= 3:
                index_key = merchant_str[:3].lower()
                if rule_key not in self.merchant_index[index_key]:
                    self.merchant_index[index_key].append(rule_key)
        else:
            rule_value = self.rules[rule_key]
            
            # 转换为字典格式（如果还不是）
            if isinstance(rule_value, dict):
                # 已经是字典格式（多分类）
                if category in rule_value:
                    # 分类已存在，增加使用次数
                    rule_value[category] += 1
                else:
                    # 新分类，添加到字典中
                    rule_value[category] = 1
            elif isinstance(rule_value, (list, tuple)):
                # 旧格式（列表）：转换为字典格式
                old_category = rule_value[0]
                old_count = rule_value[1] if len(rule_value) > 1 else 1
                if old_category == category:
                    # 分类相同，增加使用次数
                    self.rules[rule_key] = {category: old_count + 1}
                else:
                    # 分类不同，转换为多分类字典格式
                    self.rules[rule_key] = {old_category: old_count, category: 1}
            else:
                # 单个值（向后兼容）：转换为字典格式
                old_category = rule_value
                if old_category == category:
                    self.rules[rule_key] = {category: 2}
                else:
                    self.rules[rule_key] = {old_category: 1, category: 1}
        
        # 处理历史记录
        if update_existing and old_category:
            # 如果是更新操作，查找并删除旧的历史记录
            # 查找条件：相同的商户、商品、金额、账单来源和旧的分类
            # 优先删除最近添加的记录（从后往前查找）
            removed = False
            for i in range(len(self.history) - 1, -1, -1):
                h = self.history[i]
                if (h.get('merchant') == merchant_str and 
                    h.get('product', '') == product_str and
                    abs(h.get('amount', 0) - amount) < 0.01 and
                    h.get('bill_source') == bill_source and
                    h.get('category') == old_category):
                    # 找到匹配的记录，删除它
                    del self.history[i]
                    removed = True
                    break  # 只删除最近的一条匹配记录
        
        # 记录历史
        history_item = {
            'merchant': merchant_str,
            'category': category,
            'person': person,
            'bill_source': bill_source,
            'amount': amount,
            'timestamp': datetime.now().isoformat()
        }
        if product_str:
            history_item['product'] = product_str
        self.history.append(history_item)
        
        # 限制历史记录数量
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def save_data(self):
        """保存规则库和历史记录"""
        # 保存规则库
        if len(self.rules) > self.max_rules:
            rules_list = list(self.rules.items())
            
            # 排序规则：按使用次数排序
            def get_total_count(rule_value):
                """获取规则的总使用次数"""
                if isinstance(rule_value, dict):
                    # 字典格式：返回所有分类的使用次数之和
                    return sum(rule_value.values())
                elif isinstance(rule_value, (list, tuple)) and len(rule_value) > 1:
                    # 列表格式：[分类, 次数]
                    return rule_value[1]
                else:
                    # 单个值或其他格式
                    return 1
            
            rules_list.sort(key=lambda x: get_total_count(x[1]), reverse=True)
            self.rules = dict(rules_list[:self.max_rules])
        
        rules_data = {
            'version': '2.0',
            'save_time': datetime.now().isoformat(),
            'total_rules': len(self.rules),
            'rules': self.rules,
            'metadata': {
                'categories': self.config.get_categories_config()
            }
        }
        
        rules_file = self.config.get_file_path('rules_file')
        try:
            with open(rules_file, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 规则已保存到: {rules_file} ({len(self.rules)}条)")
        except Exception as e:
            print(f"❌ 保存规则失败: {e}")
        
        # 保存历史
        history_file = self.config.get_file_path('history_file')
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存历史失败: {e}")
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            'total_rules': len(self.rules),
            'total_history': len(self.history),
            'max_rules': self.max_rules,
            'max_history': self.max_history
        }