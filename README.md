# BillCategorizer

智能交互式账单分类桌面工具，支持微信、支付宝账单导入与交互式分类。通过渐进式学习分类习惯，自动分类交易记录，并导出结构化 CSV。

## 功能

- 微信 / 支付宝账单（Excel / CSV）
- GUI 图形界面（默认）与 CLI 命令行（`--cli`）
- 规则库渐进学习，支持商户+商品组合键与正则规则
- 多账单连续处理，结果页「继续 / 退出」
- 导出至 `已分类/{年份}/`，可选合并到年度总表 Excel
- PyInstaller 打包为 Windows 桌面 exe

## 项目结构

```
BillCategorizer/
├── main.py                 # 唯一入口（GUI / CLI）
├── config.py               # 配置管理
├── data_loader.py          # 账单读取与格式标准化
├── learning_engine.py      # 规则库与学习
├── categorizer.py          # 分类流程编排
├── user_interface.py       # CLI 交互
├── gui_interface.py        # GUI 入口（re-export）
├── gui/                    # GUI 子模块（对话框、交易面板、结果页等）
├── data_exporter.py        # CSV 导出
├── master_spreadsheet.py   # 年度总表合并
├── app_paths.py            # 打包后路径解析
├── bill_analyzer.py        # 可选：已分类 CSV 年度分析（需 matplotlib）
├── build.spec              # PyInstaller 打包规格
├── hooks/                  # PyInstaller runtime hooks
├── scripts/build_exe.ps1   # Windows 打包脚本
├── config.json             # 用户配置（可修改）
├── bill_rules_optimized.json   # 规则库（本地，勿提交 git）
└── bill_history.json           # 历史记录（本地，勿提交 git）
```

## 环境准备

推荐 Conda（Python 3.9+）：

```bash
conda env update --file environment.yml
```

或最小 pip 安装：

```bash
pip install pandas openpyxl pytest flake8
```

使用 `bill_analyzer.py` 时需额外安装 `matplotlib`。

## 运行

```bash
# GUI 模式（默认）
python main.py

# CLI 模式
python main.py --cli

# CLI 导出后自动合并总表
python main.py --cli --merge-master
```

### 账单文件

将微信 / 支付宝导出的 Excel 或 CSV 放在项目目录或 `原始账单/` 子目录下。程序会递归搜索。

### 导出结果

- 单账单 CSV：`已分类/{年}/{用户名}-{月}月-{来源}-已分类账单.csv`
- 年度总表（可选）：`已分类/{年}/{年}总表.xlsx`，按月份 sheet 追加；GUI 结果页可点「同步本单到总表」

总表相关配置见 `config.json` → `master_spreadsheet`（默认 `enabled: false`）。

## 测试

```bash
pytest -v
```

CI 环境下 GUI 集成测试会自动跳过；核心逻辑与总表合并有单元测试覆盖。

## 打包

```bash
# Windows
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1

# 或直接使用 PyInstaller
pyinstaller build.spec --clean --noconfirm
```

产物：`dist/BillCategorizer/BillCategorizer.exe`

将 exe 与 `config.json`、规则库 JSON（或空 `{}` / `[]`）放在同一目录；账单与导出 CSV 也放在 exe 同目录或子目录。

## 开发说明

- **唯一入口**：`python main.py`（不要使用已删除的遗留单体脚本）
- **修改分类逻辑**：`learning_engine.py`
- **修改 GUI**：`gui/` 包内各模块
- **新增账单来源**：`data_loader.py`
- 个人账单与规则库已在 `.gitignore` 中排除，请勿提交到 git

## 文档

- 架构详情：`ARCHITECTURE.md`
- 重构规划：`.planning/ROADMAP.md`
