"""
config.py - 配置管理模块
管理程序的所有配置：分类系统、文件路径、限制参数等
"""

import json
import os
import sys
import io
from datetime import datetime
from typing import Dict, List, Any, Optional


# --- 安全的编码修复（兼容 PyInstaller 打包）---
def _setup_utf8_encoding():
    """安全地设置 UTF-8 编码，避免 I/O 操作关闭错误"""
    try:
        # 仅当输出流存在且需要修复时才操作
        if hasattr(sys.stdout, "buffer") and sys.stdout.encoding.lower() != "utf-8":
            # 创建新的包装器，但保留原缓冲区的引用
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer,
                encoding="utf-8",
                errors="replace",  # 遇到无法编码的字符时替换
                line_buffering=True,
            )
        if hasattr(sys.stderr, "buffer") and sys.stderr.encoding.lower() != "utf-8":
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer,
                encoding="utf-8",
                errors="replace",
                line_buffering=True,
            )
    except (AttributeError, IOError, ValueError) as e:
        # 如果设置失败，静默忽略，不影响程序主体运行
        pass

    # 调用设置函数
    _setup_utf8_encoding()


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: str = "."):
        self.config_dir = config_dir

        # 默认配置
        self.default_config = {
            # 文件路径配置
            "files": {
                "rules_file": "bill_rules_optimized.json",
                "history_file": "bill_history.json",
                "notion_config_file": "notion_config.json",
            },
            # 性能限制
            "limits": {"max_rules": 50000, "max_history": 5000},
            # 分类系统配置
            "categories": {
                "bill_sources": ["微信", "支付宝", "银行", "现金", "其他"],
                "people_options": ["男主人", "女主人", "家庭公用"],
                "base_categories": [
                    "餐饮",
                    "出行",
                    "住房贷款",
                    "购物",
                    "生活缴费",
                    "娱乐",
                    "医疗",
                    "学习",
                    "人情往来",
                    "汽车",
                    "投资",
                    "其他消费",
                    "工资",
                    "其他",
                    "父母",
                    "党费",
                    "运动",
                    "其他收入",
                    "旅游",
                    "服务",
                    "公积金",
                    "贷款",
                    "山姆&盒马",
                    "水果&超市",
                    "买菜",
                ],
                "special_types": {
                    "转账": "人情往来",
                    "微信红包": "人情往来",
                    "收付款": "人情往来",
                },
            },
            # 显示配置
            "display": {"preview_count": 5, "progress_interval": 10},
        }

        # 运行时配置
        self.current_config = self.default_config.copy()

        # 加载自定义配置
        self._load_custom_config()

    def _load_custom_config(self):
        """加载自定义配置"""
        config_file = os.path.join(self.config_dir, "config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    custom_config = json.load(f)
                    self._merge_configs(self.current_config, custom_config)
                    print(f"✅ 已加载自定义配置: {config_file}")
            except Exception as e:
                print(f"⚠️  加载自定义配置失败: {e}")

    def _merge_configs(self, base: Dict, custom: Dict):
        """合并配置"""
        for key, value in custom.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value

    def get(self, key_path: str, default=None) -> Any:
        """获取配置值"""
        keys = key_path.split(".")
        value = self.current_config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any):
        """设置配置值"""
        keys = key_path.split(".")
        config = self.current_config

        for i, key in enumerate(keys[:-1]):
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def save_custom_config(self):
        """保存自定义配置"""
        config_file = os.path.join(self.config_dir, "config.json")
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.current_config, f, ensure_ascii=False, indent=2)
            print(f"✅ 配置已保存到: {config_file}")
            return True
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            return False

    def get_file_path(self, file_type: str) -> str:
        """获取文件路径"""
        return os.path.join(self.config_dir, self.get(f"files.{file_type}"))

    def get_limits(self) -> Dict:
        """获取限制配置"""
        return self.get("limits", {})

    def get_categories_config(self) -> Dict:
        """获取分类配置"""
        return self.get("categories", {})
