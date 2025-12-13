"""
user_interface.py - 用户交互模块
负责所有用户输入输出交互
"""

from typing import Any, Optional, List, Tuple, Dict

class UserInterface:
    """用户界面管理器"""
    
    def __init__(self, config_manager):
        self.config = config_manager
    
    def display_welcome(self):
        """显示欢迎信息"""
        print("🎯 账单自动分类助手 - 优化版")
        print("="*70)
        print("输出包含：Name, Category, Amount, Date, Person, Source")
        print("="*70)
    
    def display_transaction(self, idx: int, total: int, row: dict):
        """显示交易信息"""
        merchant = str(row.get('交易对方', '未知商户'))
        product = str(row.get('商品', '无'))
        tx_type = str(row.get('交易类型', '未知类型'))
        amount = row.get('处理后的金额', row.get('金额(元)', 0))
        date = row.get('交易时间', '未知时间')
        
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
    
    def display_classification_menu(self, suggestions: dict, base_categories: list):
        """显示分类选择菜单"""
        if suggestions:
            print("\n🤖 系统建议:")
            suggestions_list = list(suggestions.items())
            for i, (category, reason) in enumerate(suggestions_list, 1):
                print(f"  [{i}] {category} ← {reason}")
        
        print("\n🎯 基础分类:")
        start_idx = len(suggestions) + 1
        for i, category in enumerate(base_categories, start_idx):
            print(f"  [{i}] {category}")
        
        print(f"  [n] 输入新分类")
        print(f"  [s] 跳过（标记为待确认）")
        print(f"  [q] 退出程序")
    
    def get_validated_input(self, prompt: str, input_type: str = 'number', 
                           valid_range: Tuple = None, valid_options: List = None) -> Any:
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
    
    def select_bill_source(self) -> str:
        """选择账单来源"""
        bill_sources = self.config.get('categories.bill_sources', [])
        
        print("\n💳 请选择账单来源:")
        print("="*50)
        for i, source in enumerate(bill_sources, 1):
            print(f"  [{i}] {source}")
        
        choice = self.get_validated_input(
            prompt=f"\n请选择账单来源 (1-{len(bill_sources)}): ",
            input_type='number',
            valid_range=(1, len(bill_sources))
        )
        
        selected_source = bill_sources[choice-1]
        print(f"✅ 账单来源: {selected_source}")
        return selected_source
    
    def select_person_mode(self) -> Tuple[str, str]:
        """选择人员模式"""
        people_options = self.config.get('categories.people_options', [])
        
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
            return self._select_unified_person(), 'fixed'
        else:
            return '', 'per_transaction'
    
    def _select_unified_person(self) -> str:
        """选择统一人员"""
        people_options = self.config.get('categories.people_options', [])
        
        print("\n👤 请选择统一人员:")
        for i, person in enumerate(people_options, 1):
            print(f"  [{i}] {person}")
        
        choice = self.get_validated_input(
            prompt=f"\n请选择人员 (1-{len(people_options)}): ",
            input_type='number',
            valid_range=(1, len(people_options))
        )
        
        selected_person = people_options[choice-1]
        print(f"✅ 统一人员: {selected_person}")
        return selected_person
    
    def select_person_for_transaction(self, merchant: str) -> str:
        """为单条交易选择人员"""
        people_options = self.config.get('categories.people_options', [])
        
        print(f"\n交易: {merchant}")
        print("请选择人员:")
        
        for i, person in enumerate(people_options, 1):
            print(f"  [{i}] {person}")
        
        choice = self.get_validated_input(
            prompt=f"\n请选择人员 (1-{len(people_options)}): ",
            input_type='number',
            valid_range=(1, len(people_options))
        )
        
        return people_options[choice-1]
    
    def display_file_list(self, files: List[str]) -> Optional[str]:
        """显示文件列表并让用户选择"""
        if not files:
            print("❌ 未找到账单文件")
            return None
        
        print("📁 找到以下文件:")
        for i, file in enumerate(files, 1):
            print(f"  [{i}] {file}")
        
        choice = self.get_validated_input(
            prompt=f"\n请选择文件 (1-{len(files)}): ",
            input_type='number',
            valid_range=(1, len(files))
        )
        
        return files[choice-1]
    
    def display_progress(self, current: int, total: int):
        """显示处理进度"""
        if current > 0 and current % 10 == 0:
            percentage = current / total * 100
            print(f"⏳ 进度: {current}/{total} ({percentage:.1f}%)")