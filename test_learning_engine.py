"""learning_engine.py 单元测试"""
import pytest

from config import ConfigManager
from learning_engine import LearningEngine


@pytest.fixture
def engine(tmp_path):
    (tmp_path / 'bill_rules_optimized.json').write_text('{}', encoding='utf-8')
    (tmp_path / 'bill_history.json').write_text('[]', encoding='utf-8')
    config = ConfigManager(config_dir=str(tmp_path))
    return LearningEngine(config)


def test_get_suggestions_exact_match_with_product(engine):
    engine.rules = {'美团|外卖': ['餐饮', 3]}
    suggestions = engine.get_suggestions('美团', '外卖')
    assert '餐饮' in suggestions
    assert '精准匹配' in suggestions['餐饮']


def test_get_suggestions_merchant_only_key(engine):
    engine.rules = {'美团|': ['餐饮', 2]}
    suggestions = engine.get_suggestions('美团', '')
    assert suggestions.get('餐饮', '').startswith('推荐匹配')


def test_learn_from_decision_creates_rule(engine):
    engine.learn_from_decision(
        merchant='测试商户',
        category='购物',
        person='测试',
        bill_source='微信',
        amount=12.5,
        product='商品A',
    )
    assert '测试商户|商品A' in engine.rules
    value = engine.rules['测试商户|商品A']
    if isinstance(value, list):
        assert value[0] == '购物'
    else:
        assert '购物' in value


def test_regex_rule_match(engine):
    engine.rules = {'regex:美团': ['餐饮', 1]}
    suggestions = engine.get_suggestions('美团外卖', '午餐')
    assert suggestions.get('餐饮', '').startswith('正则匹配')
