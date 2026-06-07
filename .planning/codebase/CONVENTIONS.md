# Coding Conventions

**Analysis Date:** 2026-06-08

## Naming Patterns

**Files:**
- Use `snake_case.py` for all Python modules at project root: `main.py`, `categorizer.py`, `data_loader.py`, `learning_engine.py`, `gui_interface.py`, `user_interface.py`, `data_exporter.py`, `config.py`, `bill_analyzer.py`
- Each module starts with a triple-quoted module docstring describing its purpose in Chinese, e.g. `"""categorizer.py - 分类引擎主模块"""`
- Legacy monolith retained as `WeChatBillCategorizer.py` (PascalCase filename — do not follow for new files)
- Standalone scripts use descriptive names: `test_gui.py`, `build.spec`

**Classes:**
- Use `PascalCase`: `BillCategorizer`, `ConfigManager`, `DataLoader`, `LearningEngine`, `UserInterface`, `GUIInterface`, `DataExporter`, `BillAnalyzer`
- One primary class per module, named after the module's responsibility

**Functions:**
- Public functions/methods: `snake_case` — `run()`, `load_excel_file()`, `get_suggestions()`, `prepare_final_dataframe()`
- Private/internal methods: leading underscore — `_process_transactions()`, `_load_data()`, `_merge_configs()`, `_setup_utf8_encoding()`
- Module-level entry: `main(use_gui=True)` in `main.py`; standalone scripts use `if __name__ == "__main__":` guard

**Variables:**
- Instance attributes: `snake_case` — `self.config`, `self.current_bill_source`, `self.merchant_index`
- Constants in classes: `UPPER_SNAKE` in legacy code (`WeChatBillCategorizer.py`: `MAX_RULES`, `MAX_HISTORY`); prefer config via `ConfigManager.get('limits.max_rules')` in new code
- Local variables: `snake_case` — `export_df`, `person_mode`, `combined_key`

**Types:**
- Use `typing` annotations on public method signatures where present: `Optional[pd.DataFrame]`, `Dict[str, str]`, `Tuple[Optional[str], Optional[str], bool]`, `List[str]`
- Type hints are partial — not enforced on all parameters; add hints to new public APIs consistently
- `config_manager` parameters are often untyped (`def __init__(self, config_manager)`) — pass `ConfigManager` instance

**Data column naming:**
- Internal DataFrames use Chinese column names from bill sources: `交易对方`, `商品`, `交易时间`, `金额(元)`, `收/支`, `分类`, `人员`, `是否自动分类`
- Exported CSV uses English columns: `Name`, `Category`, `Amount`, `Date`, `Person`, `Source`, `是否自动分类`
- When adding loaders, normalize to the Chinese internal schema in `data_loader.py` before passing to `categorizer.py`

## Code Style

**Formatting:**
- No Black, Ruff, or isort config files detected
- CI enforces flake8 with `max-line-length=127` and `max-complexity=10` (see `.github/workflows/python-package-conda.yml`)
- Indentation: 4 spaces (no tabs)
- Blank line after imports, before class definitions
- Some inconsistent spacing: `class BillCategorizer:` has no blank line after imports in `categorizer.py`; `config.py` has a misplaced comment indent at line 11 — match surrounding file style when editing

**Linting:**
- Tool: flake8 (declared in `environment.yml` and CI)
- CI runs two passes:
  1. Hard fail: `--select=E9,F63,F7,F82` (syntax errors, undefined names)
  2. Soft warn: `--exit-zero --max-complexity=10 --max-line-length=127`
- No pre-commit hooks or `.flake8` config file — follow CI settings locally:
  ```bash
  flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
  flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
  ```

## Import Organization

**Order:**
1. Standard library (`import os`, `import json`, `from datetime import datetime`, `from typing import ...`)
2. Third-party (`import pandas as pd`, `import tkinter as tk`)
3. Local modules (`from config import ConfigManager`, `from data_loader import DataLoader`)

**Patterns:**
- No `__init__.py` package structure — all modules are flat siblings at project root
- Use direct imports, not relative imports: `from config import ConfigManager` (not `from .config import ...`)
- Lazy/conditional imports inside functions for optional deps or GUI fallbacks:
  ```python
  # main.py — GUI import with fallback
  try:
      from gui_interface import GUIInterface
      GUI_AVAILABLE = True
  except ImportError:
      GUI_AVAILABLE = False
  ```
- Import `traceback` inside except blocks when needed, not always at module top

**Path Aliases:**
- None — no `pyproject.toml` or path configuration

## Architecture Patterns

**Dependency injection via constructor:**
- Every service module receives `config_manager` in `__init__` and stores as `self.config`
- `BillCategorizer` orchestrates injected dependencies — do not instantiate sub-modules inside `categorizer.py`:
  ```python
  # main.py pattern
  config_manager = ConfigManager()
  data_loader = DataLoader(config_manager)
  learning_engine = LearningEngine(config_manager)
  user_interface = GUIInterface(config_manager)  # or UserInterface
  data_exporter = DataExporter(config_manager)
  categorizer = BillCategorizer(config_manager, data_loader, learning_engine, user_interface, data_exporter)
  ```

**UI duck typing (CLI/GUI interchangeability):**
- `GUIInterface` implements the same method surface as `UserInterface`
- `categorizer.py` detects GUI mode via `hasattr(self.ui, 'show_results')` — not via `isinstance`
- When adding UI methods, implement in both `user_interface.py` and `gui_interface.py`
- GUI-only state: `should_stop`, `current_processed_df`, `classified_data`, `categorizer` on `GUIInterface`
- CLI progress: `display_progress()` prints every N records based on `config.get('display.progress_interval')`

**Configuration access:**
- Use dot-path keys: `config.get('categories.bill_sources')`, `config.get_file_path('rules_file')`
- Defaults live in `ConfigManager.default_config` in `config.py`
- User overrides in `config.json` (merged recursively via `_merge_configs`)

## Error Handling

**Patterns:**
- **Graceful degradation with print + sentinel return:** catch `Exception`, print emoji-prefixed message, return `None`/`False`/`default`
  ```python
  # data_loader.py
  except Exception as e:
      print(f"❌ 读取文件失败: {e}")
      traceback.print_exc()
      return None
  ```
- **Top-level catch in `main.py`:** `KeyboardInterrupt` for user cancel; `Exception` shows CLI message or tkinter `messagebox.showerror` in GUI mode
- **Import failure:** print file list, `input("按回车键退出...")`, `sys.exit(1)` in `main.py`
- **GUI init fallback:** try `GUIInterface`, on failure fall back to `UserInterface` with warning print

**Avoid in new code:**
- Bare `except:` clauses (present in `gui_interface.py`, `data_exporter.py`, `bill_analyzer.py`, `main.py`) — use `except Exception:` or specific types
- Silent `pass` in except blocks without logging

**Return conventions:**
- File load failure → `None`
- Config save failure → `False`
- User quit mid-flow → `category is None` from `_process_single_transaction`
- Validation failure → retry loop in `get_validated_input()` (CLI) or dialog loop (GUI)

## Logging

**Framework:** `print()` to stdout — no `logging` module usage

**Patterns:**
- Status prefixes with emoji for scanability:
  - Success: `✅` — `print(f"✅ 规则已保存到: {rules_file}")`
  - Error: `❌` — `print(f"❌ 保存配置失败: {e}")`
  - Warning: `⚠️` — `print(f"⚠️  加载自定义配置失败: {e}")`
  - Info/action: `📖`, `🚀`, `📝`, `🎯` for read/process/transaction/welcome flows
- Debug detail: `traceback.print_exc()` on unexpected errors in `main.py` and `data_loader.py`
- Progress: conditional print in CLI via `display_progress()`; GUI uses `ttk.Progressbar`

**When adding diagnostics:**
- Follow existing emoji + Chinese message style
- Do not introduce `logging` unless refactoring the whole project

## Comments

**When to Comment:**
- Module docstring: always — one line describing module role
- Method docstrings: on non-trivial public and private methods, often in Chinese with `参数:` / `返回:` sections (see `learning_engine.py`, `data_loader.py`)
- Inline comments: explain business rules (encoding fallbacks, alipay CSV skiprows, rule migration logic, GUI/CLI branching)
- Section headers: `# --- 安全的编码修复（兼容 PyInstaller 打包）---` in `main.py` and `config.py`

**JSDoc/TSDoc:**
- Not applicable (Python project)
- Use triple-quoted docstrings; Google-style `参数:` / `返回:` blocks are the local convention

## Function Design

**Size:**
- Large files are acceptable in this codebase (`gui_interface.py` ~1527 lines, `data_loader.py` ~782 lines)
- Prefer extracting private helpers (`_load_alipay_csv`, `_remove_numbers_from_product`) over tiny one-off utilities
- `BillCategorizer.run()` is a long orchestration loop — extend via private `_process_*` methods, not inline expansion

**Parameters:**
- `config_manager` as first dependency in service constructors
- Optional behavior via method params (`person_mode: str`, `bill_source: str`) not global state
- `**kwargs` not used — explicit parameters preferred

**Return Values:**
- Data operations return `Optional[pd.DataFrame]` or `pd.DataFrame`
- UI selection methods return `str`, `Optional[str]`, or `Tuple[str, str]`
- Booleans for continue/save success: `ask_continue_processing() -> bool`, `save_custom_config() -> bool`
- Classification tuple: `(category, person, is_auto)` from `_process_single_transaction`

## Module Design

**Exports:**
- No `__all__` — classes are imported by name from module files
- No barrel `__init__.py` — flat module layout

**Barrel Files:**
- Not used

**JSON persistence:**
- Always `encoding="utf-8"` on file I/O
- `json.dump(..., ensure_ascii=False, indent=2)` for Chinese content
- Rule/history files: `bill_rules_optimized.json`, `bill_history.json` (paths from `config.py`)

**Threading (GUI only):**
- tkinter main loop on main thread (`user_interface.root.mainloop()` via `GUIInterface.run()`)
- `categorizer.run()` runs in daemon `threading.Thread` from `main.py`
- Cross-thread UI updates use `root.after()` and `threading.Event` + `queue.Queue` in `gui_interface.py`

**Encoding bootstrap:**
- `_setup_utf8_encoding()` duplicated in `main.py` and `config.py` — wraps stdout/stderr to UTF-8 for PyInstaller compatibility; call at module import time

## Adding New Code — Prescriptive Checklist

1. **New bill source parser** → add `_load_<source>_csv/excel` private methods in `data_loader.py`; output DataFrame must include standard Chinese columns
2. **New classification rule logic** → `learning_engine.py`; persist via `save_data()`
3. **New user prompt** → add method to both `user_interface.py` and `gui_interface.py`; branch in `categorizer.py` only if behavior differs by mode
4. **New export column** → `data_exporter.py` `prepare_final_dataframe()` and `export_to_csv()` filename logic
5. **New config key** → add default in `ConfigManager.default_config` in `config.py`; document in `config.json` if user-facing
6. **New entry script** → follow `bill_analyzer.py` pattern (`class` + `main()` + `if __name__ == "__main__"`)

---

*Convention analysis: 2026-06-08*
