"""
data_loader.py - 数据加载模块
负责读取和处理Excel账单文件
"""

import pandas as pd
import os
import re
from typing import Optional, Dict, Any, List
from datetime import datetime


class DataLoader:
    """数据加载器"""

    def __init__(self, config_manager):
        """
        初始化数据加载器
        参数:
            config_manager: 配置管理器实例
        """
        self.config = config_manager

    def load_excel_file(
        self, filepath: str, bill_source: str
    ) -> Optional[pd.DataFrame]:
        """
        读取账单文件（支持Excel和CSV）

        参数:
            filepath: 文件路径
            bill_source: 账单来源 ('微信', '支付宝', '银行', '现金', '其他')

        返回:
            pandas DataFrame 或 None（如果读取失败）
        """
        print(f"📖 正在读取文件: {filepath}")
        print(f"📄 账单来源: {bill_source}")

        # 根据文件扩展名选择读取方式
        file_ext = os.path.splitext(filepath)[1].lower()

        try:
            if file_ext in [".xlsx", ".xls"]:
                # Excel文件
                if bill_source == "微信":
                    return self._load_wechat_excel(filepath)
                elif bill_source == "支付宝":
                    return self._load_alipay_excel(filepath)
                else:
                    return self._load_generic_excel(filepath, bill_source)

            elif file_ext == ".csv":
                # CSV文件
                if bill_source == "微信":
                    return self._load_wechat_csv(filepath)
                elif bill_source == "支付宝":
                    return self._load_alipay_csv(filepath)
                else:
                    return self._load_generic_csv(filepath, bill_source)

            else:
                print(f"❌ 不支持的文件格式: {file_ext}")
                return None

        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _load_alipay_csv(self, filepath: str) -> Optional[pd.DataFrame]:
        """读取支付宝CSV账单文件"""
        print("📋 检测到CSV文件，尝试不同编码...")

        encodings = ["utf-8", "gbk", "gb2312", "utf-8-sig", "latin1"]

        for encoding in encodings:
            try:
                print(f"  尝试 {encoding} 编码...")

                # 先读取整个文件内容，查找数据开始行
                data_start_line = self._find_alipay_data_start_line(filepath, encoding)

                if data_start_line is None:
                    print(f"  {encoding} 编码下未找到数据开始行，继续尝试...")
                    continue

                print(f"✅ 使用 {encoding} 编码，找到数据开始行: 第{data_start_line}行")

                # 从数据开始行读取
                df = pd.read_csv(filepath, encoding=encoding, skiprows=data_start_line)

                if len(df) == 0:
                    print(f"  {encoding} 编码读取后数据为空，继续尝试...")
                    continue

                # 清理列名
                df.columns = [str(col).strip() for col in df.columns]

                print(f"✅ 使用 {encoding} 编码成功读取")
                print(f"CSV列名: {list(df.columns)}")
                print(f"CSV数据形状: {df.shape}")

                # 在转换前，先过滤掉"不计收支"的记录
                if "收/支" in df.columns:
                    original_count = len(df)
                    df = df[df["收/支"].astype(str).str.strip() != "不计收支"]
                    filtered_count = len(df)
                    if original_count > filtered_count:
                        print(f"⚠️  已过滤 {original_count - filtered_count} 条'不计收支'的记录")

                # 显示前3条数据确认
                if len(df) > 0:
                    print("\n📋 数据预览（前3条）:")
                    for i in range(min(3, len(df))):
                        row = df.iloc[i]
                        # 显示前几个字段
                        preview = {}
                        for j, col in enumerate(df.columns[:5]):  # 只显示前5列
                            preview[col] = (
                                str(row[col])[:30] if pd.notna(row[col]) else ""
                            )
                        print(f"  {i+1}. {preview}")

                # 转换为微信格式
                result = self._convert_alipay_to_wechat_format(df)

                if result is not None:
                    print(f"✅ 支付宝CSV账单处理成功，共 {len(result)} 条记录")
                    return result
                else:
                    print(f"❌ {encoding} 编码下格式转换失败")

            except UnicodeDecodeError:
                continue  # 编码错误，尝试下一个
            except Exception as e:
                print(f"  {encoding} 编码读取失败: {e}")
                continue

        print("❌ 所有编码尝试都失败")
        return None

    def _load_alipay_excel(self, filepath: str) -> Optional[pd.DataFrame]:
        """读取支付宝Excel账单文件"""
        try:
            df = pd.read_excel(filepath, engine="openpyxl")
            df.columns = [str(col).strip() for col in df.columns]

            print(f"Excel原始列名: {list(df.columns)}")

            # 转换为微信格式
            result = self._convert_alipay_to_wechat_format(df)

            if result is not None:
                print(f"✅ 支付宝Excel账单处理成功，共 {len(result)} 条记录")
                return result
            else:
                print("❌ 支付宝Excel格式转换失败")
                return None

        except Exception as e:
            print(f"❌ 读取支付宝Excel失败: {e}")
            return None

    def _load_wechat_csv(self, filepath: str) -> Optional[pd.DataFrame]:
        """读取微信CSV账单文件"""
        print("📋 检测到微信CSV文件，尝试读取...")

        encodings = ["utf-8", "gbk", "utf-8-sig"]

        for encoding in encodings:
            try:
                df = pd.read_csv(filepath, encoding=encoding)
                print(f"✅ 使用 {encoding} 编码成功读取微信CSV")

                # 清理列名
                df.columns = [str(col).strip() for col in df.columns]

                # 转换为微信格式
                result = self._standardize_to_wechat_format(df, "微信")

                if result is not None:
                    print(f"✅ 微信CSV账单处理成功，共 {len(result)} 条记录")
                    return result

            except Exception as e:
                print(f"  {encoding} 编码读取失败: {e}")
                continue

        print("❌ 微信CSV读取失败")
        return None

    def _load_wechat_excel(self, filepath: str) -> Optional[pd.DataFrame]:
        """读取微信Excel账单文件"""
        try:
            df_temp = pd.read_excel(filepath, header=None, engine="openpyxl")

            # 查找数据开始行
            start_row = self._find_wechat_data_start_row(df_temp)

            if start_row is None:
                print("❌ 无法找到微信账单数据开始行，尝试直接读取...")
                df = pd.read_excel(filepath, engine="openpyxl")
            else:
                df = pd.read_excel(filepath, skiprows=start_row, engine="openpyxl")

            df.columns = [str(col).strip() for col in df.columns]

            print(f"微信Excel列名: {list(df.columns)}")

            result = self._standardize_to_wechat_format(df, "微信")

            if result is not None:
                print(f"✅ 微信Excel账单处理成功，共 {len(result)} 条记录")
                return result
            else:
                print("❌ 微信Excel格式标准化失败")
                return None

        except Exception as e:
            print(f"❌ 读取微信Excel失败: {e}")
            return None

    def _convert_alipay_to_wechat_format(
        self, alipay_df: pd.DataFrame
    ) -> Optional[pd.DataFrame]:
        """
        将支付宝格式转换为微信格式

        支付宝列：交易时间, 交易分类, 交易对方, 对方账号, 商品说明, 收/支, 金额, 收/付款方式, 交易状态, 交易订单号, 商家订单号, 备注
        微信列：交易时间, 交易类型, 交易对方, 商品, 收/支, 金额(元), 支付方式, 当前状态, 备注
        """
        try:
            # 创建微信格式的DataFrame
            wechat_df = pd.DataFrame()

            # 显示所有可用的列，帮助调试
            print(f"📊 可用列: {list(alipay_df.columns)}")

            # 1. 交易时间 - 尝试不同的列名
            time_found = False
            time_columns = [
                "交易时间",
                "时间",
                "日期",
                "交易日期",
                "date",
                "Date",
                "DATE",
                "交易创建时间",
            ]

            for col in time_columns:
                if col in alipay_df.columns:
                    wechat_df["交易时间"] = alipay_df[col]
                    print(f"✅ 使用 '{col}' 作为交易时间列")
                    time_found = True
                    break

            if not time_found:
                # 尝试查找包含"时间"或"日期"的列
                for col in alipay_df.columns:
                    if (
                        "时间" in col
                        or "日期" in col
                        or "time" in col.lower()
                        or "date" in col.lower()
                    ):
                        wechat_df["交易时间"] = alipay_df[col]
                        print(f"✅ 使用 '{col}' 作为交易时间列（模糊匹配）")
                        time_found = True
                        break

            if not time_found:
                print("❌ 支付宝账单缺少时间列")
                # 显示前几行数据帮助调试
                print("📋 前3行数据示例:")
                print(alipay_df.head(3).to_string())
                return None

            # 2. 交易类型（使用交易分类）
            if "交易分类" in alipay_df.columns:
                wechat_df["交易类型"] = alipay_df["交易分类"]
                print(f"✅ 使用 '交易分类' 作为交易类型列")
            elif "交易类型" in alipay_df.columns:
                wechat_df["交易类型"] = alipay_df["交易类型"]
                print(f"✅ 使用 '交易类型' 作为交易类型列")
            else:
                # 尝试其他列
                type_columns = ["分类", "类型", "category", "交易种类"]
                for col in type_columns:
                    if col in alipay_df.columns:
                        wechat_df["交易类型"] = alipay_df[col]
                        print(f"✅ 使用 '{col}' 作为交易类型列")
                        break
                else:
                    wechat_df["交易类型"] = "商户消费"
                    print("⚠️  未找到交易类型列，使用默认值")

            # 3. 交易对方
            if "交易对方" in alipay_df.columns:
                wechat_df["交易对方"] = alipay_df["交易对方"]
                print(f"✅ 使用 '交易对方' 作为交易对方列")
            else:
                # 尝试其他列
                merchant_columns = [
                    "商户",
                    "对方",
                    "收款方",
                    "付款方",
                    "商户名称",
                    "对方名称",
                ]
                for col in merchant_columns:
                    if col in alipay_df.columns:
                        wechat_df["交易对方"] = alipay_df[col]
                        print(f"✅ 使用 '{col}' 作为交易对方列")
                        break
                else:
                    wechat_df["交易对方"] = "未知商户"
                    print("⚠️  未找到交易对方列，使用默认值")

            # 4. 商品（使用商品说明）
            if "商品说明" in alipay_df.columns:
                wechat_df["商品"] = alipay_df["商品说明"]
                print(f"✅ 使用 '商品说明' 作为商品列")
            elif "商品" in alipay_df.columns:
                wechat_df["商品"] = alipay_df["商品"]
                print(f"✅ 使用 '商品' 作为商品列")
            else:
                # 尝试其他列
                product_columns = ["说明", "描述", "摘要", "商品名称", "商品描述"]
                for col in product_columns:
                    if col in alipay_df.columns:
                        wechat_df["商品"] = alipay_df[col]
                        print(f"✅ 使用 '{col}' 作为商品列")
                        break
                else:
                    wechat_df["商品"] = "/"
                    print("⚠️  未找到商品列，使用默认值")

            # 5. 收/支
            if "收/支" in alipay_df.columns:
                def convert_income_expense(x):
                    x_str = str(x).strip()
                    if x_str in ["收入", "收", "转入", "收款"]:
                        return "收入"
                    elif x_str in ["支出", "支", "转出", "付款"]:
                        return "支出"
                    else:
                        return "支出"  # 默认

                wechat_df["收/支"] = alipay_df["收/支"].apply(convert_income_expense)
                print(f"✅ 使用 '收/支' 作为收/支列")
            else:
                # 尝试从金额推断或使用其他列
                amount_col = None
                for col in ["金额", "收入/支出", "收支", "交易金额"]:
                    if col in alipay_df.columns:
                        amount_col = col
                        break

                if amount_col:

                    def infer_income_expense(amount):
                        try:
                            amt_str = (
                                str(amount).replace("¥", "").replace(",", "").strip()
                            )
                            amt = float(amt_str)
                            return "收入" if amt > 0 else "支出"
                        except:
                            return "支出"

                    wechat_df["收/支"] = alipay_df[amount_col].apply(
                        infer_income_expense
                    )
                    print(f"✅ 使用 '{amount_col}' 推断收/支")
                else:
                    wechat_df["收/支"] = "支出"
                    print("⚠️  未找到收/支列，使用默认值")

            # 6. 金额(元)
            amount_found = False
            for col in ["金额", "交易金额", "收入/支出", "¥", "元"]:
                if col in alipay_df.columns:

                    def clean_amount(amount):
                        try:
                            return str(amount).replace("¥", "").replace(",", "").strip()
                        except:
                            return "0"

                    wechat_df["金额(元)"] = alipay_df[col].apply(clean_amount)
                    print(f"✅ 使用 '{col}' 作为金额列")
                    amount_found = True
                    break

            if not amount_found:
                # 查找包含"金额"的列
                for col in alipay_df.columns:
                    if (
                        "金额" in col
                        or "money" in col.lower()
                        or "amount" in col.lower()
                    ):

                        def clean_amount(amount):
                            try:
                                return (
                                    str(amount)
                                    .replace("¥", "")
                                    .replace(",", "")
                                    .strip()
                                )
                            except:
                                return "0"

                        wechat_df["金额(元)"] = alipay_df[col].apply(clean_amount)
                        print(f"✅ 使用 '{col}' 作为金额列（模糊匹配）")
                        amount_found = True
                        break

            if not amount_found:
                print("❌ 支付宝账单缺少金额列")
                return None

            # 7. 支付方式（使用收/付款方式）
            if "收/付款方式" in alipay_df.columns:
                wechat_df["支付方式"] = alipay_df["收/付款方式"]
                print(f"✅ 使用 '收/付款方式' 作为支付方式列")
            elif "支付方式" in alipay_df.columns:
                wechat_df["支付方式"] = alipay_df["支付方式"]
                print(f"✅ 使用 '支付方式' 作为支付方式列")
            else:
                wechat_df["支付方式"] = "支付宝"
                print("⚠️  未找到支付方式列，使用默认值")

            # 8. 当前状态（使用交易状态）
            if "交易状态" in alipay_df.columns:
                wechat_df["当前状态"] = alipay_df["交易状态"]
                print(f"✅ 使用 '交易状态' 作为状态列")
            else:
                wechat_df["当前状态"] = "支付成功"
                print("⚠️  未找到状态列，使用默认值")

            # 9. 备注
            if "备注" in alipay_df.columns:
                wechat_df["备注"] = alipay_df["备注"]
                print(f"✅ 使用 '备注' 作为备注列")
            else:
                wechat_df["备注"] = "/"
                print("⚠️  未找到备注列，使用默认值")

            # 预处理金额（支出为负，收入为正）
            wechat_df["处理后的金额"] = wechat_df.apply(
                lambda row: self._clean_amount(row["金额(元)"], row["收/支"]), axis=1
            )

            print(f"✅ 支付宝账单成功转换为微信格式，共 {len(wechat_df)} 条记录")

            # 显示前3条记录示例
            if len(wechat_df) > 0:
                print("\n📋 转换示例（前3条）:")
                for i in range(min(3, len(wechat_df))):
                    row = wechat_df.iloc[i]
                    time_str = str(row["交易时间"])[:19]  # 只显示前19个字符
                    merchant_str = str(row["交易对方"])[:15]
                    print(
                        f"  {i+1}. {time_str:20} | {merchant_str:15} | {row['收/支']:4} | ¥{row['金额(元)']}"
                    )

            return wechat_df

        except Exception as e:
            print(f"❌ 支付宝格式转换失败: {e}")
            import traceback

            traceback.print_exc()
            return None

    # 移除旧的 _try_alternative_alipay_loading 方法

    def _load_generic_excel(
        self, filepath: str, bill_source: str
    ) -> Optional[pd.DataFrame]:
        """读取通用Excel账单文件"""
        try:
            df = pd.read_excel(filepath, engine="openpyxl")
            df.columns = [str(col).strip() for col in df.columns]

            print(f"{bill_source}Excel列名: {list(df.columns)}")

            result = self._standardize_to_wechat_format(df, bill_source)

            if result is not None:
                print(f"✅ {bill_source}Excel账单处理成功，共 {len(result)} 条记录")
                return result
            else:
                print(f"❌ {bill_source}Excel格式标准化失败")
                return None

        except Exception as e:
            print(f"❌ 读取{bill_source}Excel失败: {e}")
            return None

    def _load_generic_csv(
        self, filepath: str, bill_source: str
    ) -> Optional[pd.DataFrame]:
        """读取通用CSV账单文件"""
        print(f"📋 检测到{bill_source}CSV文件，尝试读取...")

        encodings = ["utf-8", "gbk", "utf-8-sig", "latin1"]

        for encoding in encodings:
            try:
                df = pd.read_csv(filepath, encoding=encoding)
                print(f"✅ 使用 {encoding} 编码成功读取{bill_source}CSV")

                df.columns = [str(col).strip() for col in df.columns]

                result = self._standardize_to_wechat_format(df, bill_source)

                if result is not None:
                    print(f"✅ {bill_source}CSV账单处理成功，共 {len(result)} 条记录")
                    return result

            except Exception as e:
                print(f"  {encoding} 编码读取失败: {e}")
                continue

        print(f"❌ {bill_source}CSV读取失败")
        return None

    def find_excel_files(self, directory: str = ".") -> list:
        """查找目录中的Excel账单文件"""
        excel_files = []
        # 使用 os.walk 递归搜索所有子目录
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith((".xlsx", ".xls", ".csv")) and (
                    "微信" in file or "账单" in file or "支付宝" in file
                ):
                    # 返回相对路径（相对于directory）
                    file_path = os.path.relpath(os.path.join(root, file), directory)
                    excel_files.append(file_path)
        return excel_files

    def _find_wechat_data_start_row(self, df: pd.DataFrame) -> Optional[int]:
        """查找微信账单数据开始行"""
        for i in range(min(20, len(df))):
            row_str = " ".join(str(cell) for cell in df.iloc[i].astype(str))
            if "交易时间" in row_str and "交易类型" in row_str:
                print(f"找到微信数据开始行: 第{i}行")
                return i
        return None

    def _standardize_to_wechat_format(
        self, df: pd.DataFrame, bill_source: str
    ) -> pd.DataFrame:
        """将不同来源的账单标准化为微信格式"""
        # 确保有必要的列
        required_columns = {
            "交易时间": ["时间", "日期", "交易日期", "date"],
            "交易类型": ["类型", "分类", "交易分类", "category"],
            "交易对方": ["对方", "商户", "收款方", "付款方"],
            "商品": ["商品说明", "说明", "描述", "备注"],
            "收/支": ["收支", "类型", "方向"],
            "金额(元)": ["金额", "¥", "元", "money"],
        }

        # 创建标准化的DataFrame
        standardized_df = pd.DataFrame()

        for target_col, possible_cols in required_columns.items():
            found = False

            # 首先检查是否已经存在
            if target_col in df.columns:
                standardized_df[target_col] = df[target_col]
                found = True
            else:
                # 检查可能的列名
                for col in df.columns:
                    if any(possible in str(col).lower() for possible in possible_cols):
                        standardized_df[target_col] = df[col]
                        found = True
                        print(f"  映射: {col} -> {target_col}")
                        break

            if not found:
                # 设置默认值
                if target_col == "交易类型":
                    standardized_df[target_col] = "商户消费"
                elif target_col == "商品":
                    standardized_df[target_col] = "/"
                elif target_col == "收/支":
                    standardized_df[target_col] = "支出"
                elif target_col == "金额(元)":
                    standardized_df[target_col] = "0"
                else:
                    standardized_df[target_col] = ""

        # 添加支付方式列
        if "支付方式" in df.columns:
            standardized_df["支付方式"] = df["支付方式"]
        else:
            standardized_df["支付方式"] = bill_source

        # 添加当前状态列
        if "当前状态" in df.columns:
            standardized_df["当前状态"] = df["当前状态"]
        elif "状态" in df.columns:
            standardized_df["当前状态"] = df["状态"]
        else:
            standardized_df["当前状态"] = "成功"

        # 预处理金额
        if "金额(元)" in standardized_df.columns and "收/支" in standardized_df.columns:
            standardized_df["处理后的金额"] = standardized_df.apply(
                lambda row: self._clean_amount(row["金额(元)"], row["收/支"]), axis=1
            )

        return standardized_df

    def _clean_amount(self, amount_str: Any, transaction_type: str) -> float:
        """清理金额字符串，支出为负数，收入为正数"""
        if pd.isna(amount_str):
            return 0.0

        amount_str = str(amount_str)
        # 移除¥符号、逗号、空格
        amount_str = amount_str.replace("¥", "").replace(",", "").strip()

        try:
            amount = float(amount_str)

            if "收入" in str(transaction_type):
                return abs(amount)
            elif "支出" in str(transaction_type):
                return -abs(amount)
            else:
                # 根据金额正负推断
                if amount < 0:
                    return amount  # 已经是负数
                else:
                    # 默认按支出处理
                    return -abs(amount)

        except (ValueError, TypeError):
            # 尝试更复杂的清理
            try:
                # 移除所有非数字字符（除了负号和小数点）
                import re

                cleaned = re.sub(r"[^\d\.\-]", "", amount_str)
                amount = float(cleaned) if cleaned else 0.0

                if "收入" in str(transaction_type):
                    return abs(amount)
                else:
                    return -abs(amount)

            except:
                return 0.0

    def _find_alipay_data_start_line(
        self, filepath: str, encoding: str
    ) -> Optional[int]:
        """
        查找支付宝CSV数据开始行

        支付宝CSV特征：
        1. 前面几行是说明信息
        2. 表头行包含：交易时间,交易分类,交易对方,对方账号,商品说明,收/支,金额等
        """
        try:
            with open(filepath, "r", encoding=encoding) as f:
                lines = f.readlines()

            # 支付宝表头特征关键词
            alipay_header_keywords = [
                "交易时间",
                "交易分类",
                "交易对方",
                "商品说明",
                "收/支",
                "金额",
            ]

            # 查找包含这些关键词的行
            for i, line in enumerate(lines):
                line_str = line.strip()

                # 检查是否包含足够的支付宝特征关键词
                keyword_count = sum(
                    1 for keyword in alipay_header_keywords if keyword in line_str
                )

                if keyword_count >= 3:  # 至少有3个特征关键词
                    print(f"🔍 在第{i}行找到支付宝表头: {line_str[:100]}...")
                    return i

            # 如果没找到，尝试其他可能的表头格式
            print("⚠️  未找到标准支付宝表头，尝试其他格式...")

            for i, line in enumerate(lines):
                line_str = line.strip()

                # 检查是否是有效的CSV表头（包含逗号分隔的多个字段）
                if "," in line_str and len(line_str.split(",")) >= 5:
                    print(f"🔍 在第{i}行找到可能的CSV表头: {line_str[:100]}...")
                    return i

            print("❌ 未找到数据开始行")
            return None

        except Exception as e:
            print(f"❌ 查找数据开始行失败: {e}")
            return None


def _find_wechat_csv_data_start_line(
    self, filepath: str, encoding: str
) -> Optional[int]:
    """
    查找微信CSV数据开始行

    微信CSV特征：
    1. 前面几行是说明信息
    2. 表头行包含：交易时间,交易类型,交易对方,商品,收/支,金额(元)等
    """
    try:
        with open(filepath, "r", encoding=encoding) as f:
            lines = f.readlines()

        # 微信表头特征关键词
        wechat_header_keywords = [
            "交易时间",
            "交易类型",
            "交易对方",
            "商品",
            "收/支",
            "金额(元)",
        ]

        # 查找包含这些关键词的行
        for i, line in enumerate(lines):
            line_str = line.strip()

            # 检查是否包含足够的微信特征关键词
            keyword_count = sum(
                1 for keyword in wechat_header_keywords if keyword in line_str
            )

            if keyword_count >= 3:  # 至少有3个特征关键词
                print(f"🔍 在第{i}行找到微信表头: {line_str[:100]}...")
                return i

        print("❌ 未找到微信CSV数据开始行")
        return None

    except Exception as e:
        print(f"❌ 查找微信CSV数据开始行失败: {e}")
        return None
