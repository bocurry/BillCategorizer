<!-- GSD:project-start source:PROJECT.md -->

## Project

**BillCategorizer**

BillCategorizer 是一个面向个人/家庭使用的智能账单分类桌面工具，支持微信、支付宝账单的导入与交互式分类。通过渐进式学习用户的分类习惯，自动对交易记录进行分类，并导出结构化 CSV。本次工作是对现有棕地代码库的大幅重构，而非从零新建。

**Core Value:** 用户能够稳定、流畅地完成「导入账单 → 分类（自动+手动）→ 导出已分类 CSV」的完整流程；GUI 模式下处理多个账单时不卡死、可正常关闭窗口。

### Constraints

- **Tech stack**: 保持 Python + tkinter + pandas — 用户本地 Conda 环境已配置，避免引入重型新框架
- **Compatibility**: 现有 `bill_rules_optimized.json` 规则库需向后兼容或提供迁移
- **Data privacy**: 个人账单数据不得提交到 git
- **Entry point**: 打包与文档统一指向 `main.py`

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.9 — 全部应用逻辑（`main.py`、`categorizer.py`、`data_loader.py`、`learning_engine.py`、`gui_interface.py` 等）
- Python 3.10 — GitHub Actions CI 构建矩阵（`.github/workflows/python-package-conda.yml`）
- JSON — 配置与持久化（`config.json`、`bill_rules_optimized.json`、`bill_history.json`）
- YAML — Conda 环境定义（`environment.yml`）
- Markdown — 项目文档（`README.md`、`ARCHITECTURE.md`）

## Runtime

- CPython（Conda `base` 环境，Python 3.9）
- 桌面单机应用，无 Web 服务器或长期运行服务进程
- Conda（主依赖来源，`environment.yml`）
- pip（`environment.yml` 中 `pip:` 段及 CI Windows 任务直接安装）
- Lockfile: missing（无 `requirements.txt`、`poetry.lock`、`Pipfile.lock` 或 conda-lock）

## Frameworks

- tkinter（Python 标准库）— GUI 主界面（`gui_interface.py`）、文件选择对话框、消息框；`bill_analyzer.py` 也使用 tkinter 选文件
- pandas — 账单 DataFrame 读写、转换、导出（`data_loader.py`、`categorizer.py`、`data_exporter.py`）
- openpyxl — Excel（`.xlsx`/`.xls`）读取引擎（`data_loader.py`、`main.py` 启动时校验）
- pytest — GUI 冒烟测试（`test_gui.py`）；CI 中 `pytest -v`
- flake8 — 语法与风格检查（CI lint 步骤）
- PyInstaller — 打包为桌面可执行文件（`build.spec`；CI 调用 `pyinstaller build.spec`）
- Black（`ms-python.black-formatter`）— VS Code 保存时格式化（`.vscode/settings.json`）
- GitHub Actions — 跨平台 CI/CD（`.github/workflows/python-package-conda.yml`）
- Xvfb — Linux CI 中虚拟显示，用于 GUI 测试环境准备

## Key Dependencies

- `pandas` — 账单解析、分类流水线、CSV 导出
- `openpyxl` — 微信/支付宝 Excel 账单导入
- `tkinter` — 默认 GUI 模式（`main.py` 中 `GUI_AVAILABLE`）
- `matplotlib` — 年度收支分析与图表生成（`bill_analyzer.py`）；需单独 `pip install matplotlib`
- `pickle`、`gzip` — 遗留单体脚本规则持久化（`WeChatBillCategorizer.py`）
- `python-docx` — 在 `environment.yml` 的 pip 段列出，源码中无 `docx` 导入
- `pyinstaller` — CI 构建步骤安装，生成 `dist/BillCategorizer/`
- `pytest`、`flake8` — 开发与 CI 质量门禁

## Configuration

- 无 `.env` 文件；不通过环境变量驱动业务逻辑
- 运行时配置来自 JSON 文件，由 `ConfigManager`（`config.py`）加载与合并
- 关键配置文件：
- `build.spec` — 主 PyInstaller 规格：入口 `main.py`，捆绑 `config.json`、`bill_rules_optimized.json`、`bill_history.json`，`hiddenimports` 含 pandas/openpyxl/tkinter，`console=False`（窗口模式）
- `main.spec` — 备用/简化 PyInstaller 规格（`console=True`，无 data 文件捆绑）；CI 使用 `build.spec`
- `environment.yml` — Conda 环境：`python=3.9`、`pandas`、`openpyxl`，pip 段含 `pytest`、`flake8`、`python-docx`
- `.vscode/settings.json` — `formatOnSave: true`，默认格式化器 Black

## Platform Requirements

- Python 3.9+（推荐 Conda：`conda env update --file environment.yml`）
- Windows 或 Linux 桌面环境（tkinter 需系统 GUI 支持；Linux 开发/CI 可用 Xvfb）
- 手动安装 `pandas`、`openpyxl`（README 亦说明 `pip install pandas openpyxl`）
- 使用 `bill_analyzer.py` 时需额外安装 `matplotlib`
- 目标为本地桌面分发，非云服务部署
- PyInstaller 产物：`dist/BillCategorizer/`（Windows/Linux CI artifact，保留 30 天）
- 运行方式：`python main.py`（GUI 默认）或 `python main.py --cli`（命令行）
- 输入：用户从微信/支付宝导出的 Excel/CSV 本地文件（`原始账单/` 等目录）
- 输出：本地 CSV（`{用户名}-{月份}-{来源}-已分类账单.csv`）及 JSON 规则/历史更新

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Use `snake_case.py` for all Python modules at project root: `main.py`, `categorizer.py`, `data_loader.py`, `learning_engine.py`, `gui_interface.py`, `user_interface.py`, `data_exporter.py`, `config.py`, `bill_analyzer.py`
- Each module starts with a triple-quoted module docstring describing its purpose in Chinese, e.g. `"""categorizer.py - 分类引擎主模块"""`
- Legacy monolith retained as `WeChatBillCategorizer.py` (PascalCase filename — do not follow for new files)
- Standalone scripts use descriptive names: `test_gui.py`, `build.spec`
- Use `PascalCase`: `BillCategorizer`, `ConfigManager`, `DataLoader`, `LearningEngine`, `UserInterface`, `GUIInterface`, `DataExporter`, `BillAnalyzer`
- One primary class per module, named after the module's responsibility
- Public functions/methods: `snake_case` — `run()`, `load_excel_file()`, `get_suggestions()`, `prepare_final_dataframe()`
- Private/internal methods: leading underscore — `_process_transactions()`, `_load_data()`, `_merge_configs()`, `_setup_utf8_encoding()`
- Module-level entry: `main(use_gui=True)` in `main.py`; standalone scripts use `if __name__ == "__main__":` guard
- Instance attributes: `snake_case` — `self.config`, `self.current_bill_source`, `self.merchant_index`
- Constants in classes: `UPPER_SNAKE` in legacy code (`WeChatBillCategorizer.py`: `MAX_RULES`, `MAX_HISTORY`); prefer config via `ConfigManager.get('limits.max_rules')` in new code
- Local variables: `snake_case` — `export_df`, `person_mode`, `combined_key`
- Use `typing` annotations on public method signatures where present: `Optional[pd.DataFrame]`, `Dict[str, str]`, `Tuple[Optional[str], Optional[str], bool]`, `List[str]`
- Type hints are partial — not enforced on all parameters; add hints to new public APIs consistently
- `config_manager` parameters are often untyped (`def __init__(self, config_manager)`) — pass `ConfigManager` instance
- Internal DataFrames use Chinese column names from bill sources: `交易对方`, `商品`, `交易时间`, `金额(元)`, `收/支`, `分类`, `人员`, `是否自动分类`
- Exported CSV uses English columns: `Name`, `Category`, `Amount`, `Date`, `Person`, `Source`, `是否自动分类`
- When adding loaders, normalize to the Chinese internal schema in `data_loader.py` before passing to `categorizer.py`

## Code Style

- No Black, Ruff, or isort config files detected
- CI enforces flake8 with `max-line-length=127` and `max-complexity=10` (see `.github/workflows/python-package-conda.yml`)
- Indentation: 4 spaces (no tabs)
- Blank line after imports, before class definitions
- Some inconsistent spacing: `class BillCategorizer:` has no blank line after imports in `categorizer.py`; `config.py` has a misplaced comment indent at line 11 — match surrounding file style when editing
- Tool: flake8 (declared in `environment.yml` and CI)
- CI runs two passes:
- No pre-commit hooks or `.flake8` config file — follow CI settings locally:

## Import Organization

- No `__init__.py` package structure — all modules are flat siblings at project root
- Use direct imports, not relative imports: `from config import ConfigManager` (not `from .config import ...`)
- Lazy/conditional imports inside functions for optional deps or GUI fallbacks:
- Import `traceback` inside except blocks when needed, not always at module top
- None — no `pyproject.toml` or path configuration

## Architecture Patterns

- Every service module receives `config_manager` in `__init__` and stores as `self.config`
- `BillCategorizer` orchestrates injected dependencies — do not instantiate sub-modules inside `categorizer.py`:
- `GUIInterface` implements the same method surface as `UserInterface`
- `categorizer.py` detects GUI mode via `hasattr(self.ui, 'show_results')` — not via `isinstance`
- When adding UI methods, implement in both `user_interface.py` and `gui_interface.py`
- GUI-only state: `should_stop`, `current_processed_df`, `classified_data`, `categorizer` on `GUIInterface`
- CLI progress: `display_progress()` prints every N records based on `config.get('display.progress_interval')`
- Use dot-path keys: `config.get('categories.bill_sources')`, `config.get_file_path('rules_file')`
- Defaults live in `ConfigManager.default_config` in `config.py`
- User overrides in `config.json` (merged recursively via `_merge_configs`)

## Error Handling

- **Graceful degradation with print + sentinel return:** catch `Exception`, print emoji-prefixed message, return `None`/`False`/`default`
- **Top-level catch in `main.py`:** `KeyboardInterrupt` for user cancel; `Exception` shows CLI message or tkinter `messagebox.showerror` in GUI mode
- **Import failure:** print file list, `input("按回车键退出...")`, `sys.exit(1)` in `main.py`
- **GUI init fallback:** try `GUIInterface`, on failure fall back to `UserInterface` with warning print
- Bare `except:` clauses (present in `gui_interface.py`, `data_exporter.py`, `bill_analyzer.py`, `main.py`) — use `except Exception:` or specific types
- Silent `pass` in except blocks without logging
- File load failure → `None`
- Config save failure → `False`
- User quit mid-flow → `category is None` from `_process_single_transaction`
- Validation failure → retry loop in `get_validated_input()` (CLI) or dialog loop (GUI)

## Logging

- Status prefixes with emoji for scanability:
- Debug detail: `traceback.print_exc()` on unexpected errors in `main.py` and `data_loader.py`
- Progress: conditional print in CLI via `display_progress()`; GUI uses `ttk.Progressbar`
- Follow existing emoji + Chinese message style
- Do not introduce `logging` unless refactoring the whole project

## Comments

- Module docstring: always — one line describing module role
- Method docstrings: on non-trivial public and private methods, often in Chinese with `参数:` / `返回:` sections (see `learning_engine.py`, `data_loader.py`)
- Inline comments: explain business rules (encoding fallbacks, alipay CSV skiprows, rule migration logic, GUI/CLI branching)
- Section headers: `# --- 安全的编码修复（兼容 PyInstaller 打包）---` in `main.py` and `config.py`
- Not applicable (Python project)
- Use triple-quoted docstrings; Google-style `参数:` / `返回:` blocks are the local convention

## Function Design

- Large files are acceptable in this codebase (`gui_interface.py` ~1527 lines, `data_loader.py` ~782 lines)
- Prefer extracting private helpers (`_load_alipay_csv`, `_remove_numbers_from_product`) over tiny one-off utilities
- `BillCategorizer.run()` is a long orchestration loop — extend via private `_process_*` methods, not inline expansion
- `config_manager` as first dependency in service constructors
- Optional behavior via method params (`person_mode: str`, `bill_source: str`) not global state
- `**kwargs` not used — explicit parameters preferred
- Data operations return `Optional[pd.DataFrame]` or `pd.DataFrame`
- UI selection methods return `str`, `Optional[str]`, or `Tuple[str, str]`
- Booleans for continue/save success: `ask_continue_processing() -> bool`, `save_custom_config() -> bool`
- Classification tuple: `(category, person, is_auto)` from `_process_single_transaction`

## Module Design

- No `__all__` — classes are imported by name from module files
- No barrel `__init__.py` — flat module layout
- Not used
- Always `encoding="utf-8"` on file I/O
- `json.dump(..., ensure_ascii=False, indent=2)` for Chinese content
- Rule/history files: `bill_rules_optimized.json`, `bill_history.json` (paths from `config.py`)
- tkinter main loop on main thread (`user_interface.root.mainloop()` via `GUIInterface.run()`)
- `categorizer.run()` runs in daemon `threading.Thread` from `main.py`
- Cross-thread UI updates use `root.after()` and `threading.Event` + `queue.Queue` in `gui_interface.py`
- `_setup_utf8_encoding()` duplicated in `main.py` and `config.py` — wraps stdout/stderr to UTF-8 for PyInstaller compatibility; call at module import time

## Adding New Code — Prescriptive Checklist

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Entry / bootstrap | UTF-8 fix, dependency check, module wiring, GUI/CLI mode selection, thread startup | `main.py` |
| ConfigManager | Default + merged config, dot-path get/set, file path resolution | `config.py` |
| DataLoader | Discover bill files, detect encoding, parse WeChat/Alipay Excel/CSV, normalize columns, filter invalid rows | `data_loader.py` |
| LearningEngine | Load/save rules & history, merchant index, suggestions (exact/regex/fuzzy), learn from user decisions | `learning_engine.py` |
| BillCategorizer | Main workflow loop, per-transaction classification, stats, merge GUI edits before export | `categorizer.py` |
| UserInterface | CLI prompts for source/file/person/category; input validation | `user_interface.py` |
| GUIInterface | Tkinter dialogs, transaction window, classified-list edit/delete, results preview; duck-types UserInterface API | `gui_interface.py` |
| DataExporter | Map internal DataFrame → export schema; write CSV with naming convention | `data_exporter.py` |
| BillAnalyzer (standalone) | Annual/monthly income-expense analysis and charts from classified CSV | `bill_analyzer.py` |
| Legacy monolith | Pre-modular single-file categorizer (superseded by modular stack) | `WeChatBillCategorizer.py` |

## Pattern Overview

- All modules live as flat top-level `.py` files; no Python package namespace (`src/` or `bill_categorizer/`).
- `BillCategorizer` receives every collaborator via `__init__`; it does not import UI or loader implementations directly beyond what `main.py` injects.
- `UserInterface` and `GUIInterface` expose the same method surface (`select_bill_source`, `display_file_list`, `get_validated_input`, etc.); the orchestrator picks behavior with duck typing (`hasattr(self.ui, 'show_results')` for GUI detection).
- Stateful learning persists to JSON on disk; in-memory `pandas.DataFrame` carries per-session classification columns (`分类`, `人员`, `是否自动分类`).
- GUI mode runs Tkinter on the main thread and `BillCategorizer.run()` on a daemon background thread (`main.py`).

## Layers

- Purpose: Collect user choices (source, file, person, category) and display progress/results.
- Location: `user_interface.py`, `gui_interface.py`
- Contains: I/O only; no file parsing or rule logic.
- Depends on: `ConfigManager` (category/person lists).
- Used by: `BillCategorizer` via injected `self.ui`.
- Purpose: End-to-end classification session — loop over bills, iterate transactions, coordinate learning and export.
- Location: `categorizer.py`
- Contains: `BillCategorizer` class, stats (`defaultdict`), batch `while True` loop.
- Depends on: all other core modules via constructor args.
- Used by: `main.py`.
- Purpose: Classification intelligence — rule keys, suggestion ranking, history append, rule cap enforcement.
- Location: `learning_engine.py`
- Contains: `LearningEngine`, `merchant_index`, rule migration (`_migrate_rules`).
- Depends on: `ConfigManager` for paths and limits.
- Used by: `BillCategorizer`; GUI edit flow calls `learn_from_decision(..., update_existing=True)` via `self.categorizer` reference.
- Purpose: External data read/write and configuration.
- Location: `data_loader.py`, `data_exporter.py`, `config.py`
- Contains: pandas I/O, column standardization, CSV export naming.
- Depends on: `ConfigManager`; stdlib + pandas/openpyxl.
- Used by: `BillCategorizer`, `main.py`.

## Data Flow

### Primary Request Path

### GUI Edit-Before-Export Flow

### Internal Data Shape Transitions

```text

```

- **Rules/history:** JSON files loaded at `LearningEngine.__init__`, saved after each bill batch via `save_data()`.
- **Session stats:** `BillCategorizer.stats` reset per bill in the outer loop.
- **GUI session state:** `GUIInterface.current_processed_df`, `classified_data`, `should_stop` flag for cooperative cancellation.
- **Config mutations:** New categories added at runtime via `config.set()` + `save_custom_config()` when user enters `[n]` new category (`categorizer.py:357-362`).

## Key Abstractions

- Purpose: Single source of truth for categories, people, file paths, display limits.
- Examples: `config.py`, consumed by every module.
- Pattern: Dot-path accessor (`get("categories.base_categories")`), deep-merge from `config.json`.
- Purpose: Swap CLI vs GUI without changing orchestrator logic.
- Examples: `user_interface.py`, `gui_interface.py`
- Pattern: Shared method names; GUI adds `show_results`, `add_classified_transaction`, `run`, `should_stop`. Detection: `hasattr(self.ui, 'show_results')`.
- Purpose: Granular learning beyond merchant-only keys.
- Examples: `learning_engine.py` — keys like `"美团|外卖"`, `"美团|"`, legacy plain merchant keys, optional `"regex:pattern"`.
- Pattern: Dict value is either `[category, count]` or `{category: count}` for multi-category rules.
- Purpose: Uniform processing regardless of bill source.
- Examples: Produced in `data_loader.py` `_standardize_to_wechat_format()`.
- Pattern: pandas Series/dict with Chinese canonical column names consumed by `categorizer._process_single_transaction()`.

## Entry Points

- Location: `main.py`
- Triggers: `python main.py` or PyInstaller exe from `build.spec`
- Responsibilities: Module bootstrap, `--cli` flag, GUI thread orchestration, error dialogs.
- Location: `WeChatBillCategorizer.py`
- Triggers: Direct script execution (`if __name__ == "__main__"`)
- Responsibilities: Monolithic `OptimizedBillCategorizer` — self-contained rules, UI, export. Not wired into modular `main.py`.
- Location: `bill_analyzer.py`
- Triggers: Direct script execution
- Responsibilities: Read classified CSV, aggregate by year/month/quarter, matplotlib charts. Independent of classification pipeline.
- Location: `test_gui.py`
- Triggers: `pytest` (skipped in CI via env check)
- Responsibilities: Smoke-test Tkinter window creation for PyInstaller diagnostics.

## Architectural Constraints

- **Threading:** Tkinter main loop must run on main thread; classification runs on daemon thread in GUI mode (`main.py:131-163`). UI updates use `root.update_idletasks()` from worker thread (`categorizer.py:219-223`).
- **Global state:** Module-level UTF-8 setup in `main.py` and `config.py`. No shared singletons beyond injected instances.
- **Circular imports:** None detected; dependency graph is acyclic: `main` → all modules; `categorizer` does not import `main` or `gui_interface` directly.
- **Working directory coupling:** JSON config/rules and CSV output paths resolve relative to `ConfigManager.config_dir` (default `"."`). Running from a different cwd changes data file locations.
- **Duplicate tree:** Nested `BillCategorizer/` subdirectory contains an older copy of core modules with fewer features (e.g., simpler `learning_engine.py`). Canonical source is repository root — do not edit the nested copy for new work.

## Anti-Patterns

### Duck-typing GUI detection everywhere

### GUI worker thread calling Tkinter without queue

### Legacy monolith coexisting with modular stack

## Error Handling

- File read failures: `data_loader.load_excel_file()` catches exceptions, prints traceback, returns `None` (`data_loader.py:66-71`).
- Import failures: `main.py` prints missing module list and `sys.exit(1)` (`main.py:68-78`).
- GUI init failure: falls back to `UserInterface` (`main.py:106-115`).
- Classification interrupt: user `q` returns `(None, None, False)`; partial DataFrame exported only if rows processed (`categorizer.py:209-212`, `227-275`).
- JSON load/save: try/except with console warnings in `LearningEngine` and `ConfigManager`.

## Cross-Cutting Concerns

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
