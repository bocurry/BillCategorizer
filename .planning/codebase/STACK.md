# Technology Stack

**Analysis Date:** 2026-06-08

## Languages

**Primary:**
- Python 3.9 — 全部应用逻辑（`main.py`、`categorizer.py`、`data_loader.py`、`learning_engine.py`、`gui_interface.py` 等）
- Python 3.10 — GitHub Actions CI 构建矩阵（`.github/workflows/python-package-conda.yml`）

**Secondary:**
- JSON — 配置与持久化（`config.json`、`bill_rules_optimized.json`、`bill_history.json`）
- YAML — Conda 环境定义（`environment.yml`）
- Markdown — 项目文档（`README.md`、`ARCHITECTURE.md`）

## Runtime

**Environment:**
- CPython（Conda `base` 环境，Python 3.9）
- 桌面单机应用，无 Web 服务器或长期运行服务进程

**Package Manager:**
- Conda（主依赖来源，`environment.yml`）
- pip（`environment.yml` 中 `pip:` 段及 CI Windows 任务直接安装）
- Lockfile: missing（无 `requirements.txt`、`poetry.lock`、`Pipfile.lock` 或 conda-lock）

## Frameworks

**Core:**
- tkinter（Python 标准库）— GUI 主界面（`gui_interface.py`）、文件选择对话框、消息框；`bill_analyzer.py` 也使用 tkinter 选文件
- pandas — 账单 DataFrame 读写、转换、导出（`data_loader.py`、`categorizer.py`、`data_exporter.py`）
- openpyxl — Excel（`.xlsx`/`.xls`）读取引擎（`data_loader.py`、`main.py` 启动时校验）

**Testing:**
- pytest — GUI 冒烟测试（`test_gui.py`）；CI 中 `pytest -v`
- flake8 — 语法与风格检查（CI lint 步骤）

**Build/Dev:**
- PyInstaller — 打包为桌面可执行文件（`build.spec`；CI 调用 `pyinstaller build.spec`）
- Black（`ms-python.black-formatter`）— VS Code 保存时格式化（`.vscode/settings.json`）
- GitHub Actions — 跨平台 CI/CD（`.github/workflows/python-package-conda.yml`）
- Xvfb — Linux CI 中虚拟显示，用于 GUI 测试环境准备

## Key Dependencies

**Critical（主流程必需）:**
- `pandas` — 账单解析、分类流水线、CSV 导出
- `openpyxl` — 微信/支付宝 Excel 账单导入
- `tkinter` — 默认 GUI 模式（`main.py` 中 `GUI_AVAILABLE`）

**辅助/独立脚本（未列入 `environment.yml` 主依赖，但代码中使用）:**
- `matplotlib` — 年度收支分析与图表生成（`bill_analyzer.py`）；需单独 `pip install matplotlib`
- `pickle`、`gzip` — 遗留单体脚本规则持久化（`WeChatBillCategorizer.py`）

**`environment.yml` 声明但主代码未引用:**
- `python-docx` — 在 `environment.yml` 的 pip 段列出，源码中无 `docx` 导入

**Infrastructure（打包与 CI）:**
- `pyinstaller` — CI 构建步骤安装，生成 `dist/BillCategorizer/`
- `pytest`、`flake8` — 开发与 CI 质量门禁

## Configuration

**Environment:**
- 无 `.env` 文件；不通过环境变量驱动业务逻辑
- 运行时配置来自 JSON 文件，由 `ConfigManager`（`config.py`）加载与合并
- 关键配置文件：
  - `config.json` — 分类体系、人员选项、文件路径、性能上限
  - `bill_rules_optimized.json` — 商户→分类规则库
  - `bill_history.json` — 分类历史记录
  - `notion_config.json` — 配置项中预留路径（`config.py` → `files.notion_config_file`），文件与集成代码均未实现

**Build:**
- `build.spec` — 主 PyInstaller 规格：入口 `main.py`，捆绑 `config.json`、`bill_rules_optimized.json`、`bill_history.json`，`hiddenimports` 含 pandas/openpyxl/tkinter，`console=False`（窗口模式）
- `main.spec` — 备用/简化 PyInstaller 规格（`console=True`，无 data 文件捆绑）；CI 使用 `build.spec`
- `environment.yml` — Conda 环境：`python=3.9`、`pandas`、`openpyxl`，pip 段含 `pytest`、`flake8`、`python-docx`

**IDE:**
- `.vscode/settings.json` — `formatOnSave: true`，默认格式化器 Black

## Platform Requirements

**Development:**
- Python 3.9+（推荐 Conda：`conda env update --file environment.yml`）
- Windows 或 Linux 桌面环境（tkinter 需系统 GUI 支持；Linux 开发/CI 可用 Xvfb）
- 手动安装 `pandas`、`openpyxl`（README 亦说明 `pip install pandas openpyxl`）
- 使用 `bill_analyzer.py` 时需额外安装 `matplotlib`

**Production:**
- 目标为本地桌面分发，非云服务部署
- PyInstaller 产物：`dist/BillCategorizer/`（Windows/Linux CI artifact，保留 30 天）
- 运行方式：`python main.py`（GUI 默认）或 `python main.py --cli`（命令行）
- 输入：用户从微信/支付宝导出的 Excel/CSV 本地文件（`原始账单/` 等目录）
- 输出：本地 CSV（`{用户名}-{月份}-{来源}-已分类账单.csv`）及 JSON 规则/历史更新

---

*Stack analysis: 2026-06-08*
