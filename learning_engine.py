"""
learning_engine.py - 学习引擎模块
负责规则库的管理、学习和查询
"""

import json
import os
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
        
        # 加载历史记录
        history_file = self.config.get_file_path('history_file')
        self.history = self._load_json_file(history_file, [], self.max_history)
        
        # 构建索引
        self._build_merchant_index()
    
    def _load_rules_with_limit(self, filename: str, max_rules: int) -> Dict:
        """加载规则库并限制数量"""
        if not os.path.exists(filename):
            return {}
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                rules = data.get('rules', {})
                
                # 限制规则数量
                if len(rules) > max_rules:
                    print(f"⚠️  规则数量过多({len(rules)})，保留最常用的{max_rules}条")
                    sorted_rules = sorted(rules.items(), 
                                        key=lambda x: x[1][1] if isinstance(x[1], list) and len(x[1]) > 1 else 0,
                                        reverse=True)
                    rules = dict(sorted_rules[:max_rules])
                
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
    
    def _build_merchant_index(self):
        """构建商户名关键词索引"""
        self.merchant_index = defaultdict(list)
        for merchant in self.rules.keys():
            if isinstance(merchant, str) and len(merchant) > 1:
                # 提取前3个字符作为索引
                key = merchant[:3].lower()
                self.merchant_index[key].append(merchant)
    
    def get_suggestions(self, merchant: str, transaction_type: str) -> Dict[str, str]:
        """
        获取分类建议
        
        参数:
            merchant: 商户名
            transaction_type: 交易类型
        
        返回:
            建议字典 {分类: 理由}
        """
        suggestions = {}
        merchant_str = str(merchant)
        
        # 精确匹配
        if merchant_str in self.rules:
            if isinstance(self.rules[merchant_str], (list, tuple)):
                category = self.rules[merchant_str][0]
            else:
                category = self.rules[merchant_str]
            suggestions[category] = f"精确匹配: {merchant_str}"
        
        # 模糊匹配（使用索引加速）
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
    
    def learn_from_decision(self, merchant: str, category: str, 
                           person: str, bill_source: str, amount: float,
                           update_existing: bool = False, old_category: str = None):
        """
        从用户决策中学习
        
        参数:
            merchant: 商户名
            category: 用户选择的分类
            person: 人员
            bill_source: 账单来源
            amount: 金额
            update_existing: 是否更新已存在的记录（用于修改分类时）
            old_category: 旧的分类（用于查找要更新的记录）
        """
        # 更新规则库
        if merchant not in self.rules:
            self.rules[merchant] = [category, 1]
            # 更新索引
            if len(merchant) >= 3:
                index_key = merchant[:3].lower()
                self.merchant_index[index_key].append(merchant)
        else:
            if isinstance(self.rules[merchant], (list, tuple)):
                # 如果分类发生变化，更新分类；否则增加使用次数
                if self.rules[merchant][0] != category:
                    self.rules[merchant][0] = category
                    # 分类变化时，重置使用次数为1（因为这是新的分类）
                    self.rules[merchant][1] = 1
                else:
                    self.rules[merchant][1] += 1
            else:
                self.rules[merchant] = [self.rules[merchant], 2]
        
        # 处理历史记录
        if update_existing and old_category:
            # 如果是更新操作，查找并删除旧的历史记录
            # 查找条件：相同的商户、金额、账单来源和旧的分类
            # 优先删除最近添加的记录（从后往前查找）
            removed = False
            for i in range(len(self.history) - 1, -1, -1):
                h = self.history[i]
                if (h.get('merchant') == merchant and 
                    abs(h.get('amount', 0) - amount) < 0.01 and
                    h.get('bill_source') == bill_source and
                    h.get('category') == old_category):
                    # 找到匹配的记录，删除它
                    del self.history[i]
                    removed = True
                    break  # 只删除最近的一条匹配记录
        
        # 记录历史
        self.history.append({
            'merchant': merchant,
            'category': category,
            'person': person,
            'bill_source': bill_source,
            'amount': amount,
            'timestamp': datetime.now().isoformat()
        })
        
        # 限制历史记录数量
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def save_data(self):
        """保存规则库和历史记录"""
        # 保存规则库
        if len(self.rules) > self.max_rules:
            rules_list = list(self.rules.items())
            if all(isinstance(v, (list, tuple)) and len(v) > 1 for v in self.rules.values()):
                rules_list.sort(key=lambda x: x[1][1], reverse=True)
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