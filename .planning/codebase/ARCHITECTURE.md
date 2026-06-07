<!-- refreshed: 2026-06-08 -->
# Architecture

**Analysis Date:** 2026-06-08

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                     Presentation Layer                               │
├──────────────────────────────┬──────────────────────────────────────┤
│   CLI: `user_interface.py`   │   GUI: `gui_interface.py`            │
│   (stdin/stdout prompts)     │   (Tkinter + threading.Event sync)   │
└──────────────┬───────────────┴──────────────────┬───────────────────┘
               │                                   │
               └──────────────┬────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Application / Orchestration Layer                       │
│                    `categorizer.py` → BillCategorizer                │
│   (batch loop, per-transaction flow, stats, export coordination)     │
└──────────────┬───────────────────────────────┬────────────────────┘
               │                               │
               ▼                               ▼
┌──────────────────────────┐    ┌─────────────────────────────────────┐
│   Domain Layer            │    │   Infrastructure Layer               │
│   `learning_engine.py`    │    │   `data_loader.py`  (read/normalize) │
│   (rules, suggestions,    │    │   `data_exporter.py` (transform/out) │
│    history, persistence)  │    │   `config.py` (ConfigManager)        │
└──────────────┬───────────┘    └──────────────────┬──────────────────┘
               │                                    │
               └────────────────┬───────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Local JSON + CSV Persistence (working directory)                    │
│  `config.json`, `bill_rules_optimized.json`, `bill_history.json`     │
│  Output: `{person}-{month}-{source}-已分类账单.csv`                   │
└─────────────────────────────────────────────────────────────────────┘
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

**Overall:** Layered modular monolith with constructor-based dependency injection and a Strategy-like UI abstraction.

**Key Characteristics:**
- All modules live as flat top-level `.py` files; no Python package namespace (`src/` or `bill_categorizer/`).
- `BillCategorizer` receives every collaborator via `__init__`; it does not import UI or loader implementations directly beyond what `main.py` injects.
- `UserInterface` and `GUIInterface` expose the same method surface (`select_bill_source`, `display_file_list`, `get_validated_input`, etc.); the orchestrator picks behavior with duck typing (`hasattr(self.ui, 'show_results')` for GUI detection).
- Stateful learning persists to JSON on disk; in-memory `pandas.DataFrame` carries per-session classification columns (`分类`, `人员`, `是否自动分类`).
- GUI mode runs Tkinter on the main thread and `BillCategorizer.run()` on a daemon background thread (`main.py`).

## Layers

**Presentation (UI):**
- Purpose: Collect user choices (source, file, person, category) and display progress/results.
- Location: `user_interface.py`, `gui_interface.py`
- Contains: I/O only; no file parsing or rule logic.
- Depends on: `ConfigManager` (category/person lists).
- Used by: `BillCategorizer` via injected `self.ui`.

**Application (Orchestration):**
- Purpose: End-to-end classification session — loop over bills, iterate transactions, coordinate learning and export.
- Location: `categorizer.py`
- Contains: `BillCategorizer` class, stats (`defaultdict`), batch `while True` loop.
- Depends on: all other core modules via constructor args.
- Used by: `main.py`.

**Domain (Learning):**
- Purpose: Classification intelligence — rule keys, suggestion ranking, history append, rule cap enforcement.
- Location: `learning_engine.py`
- Contains: `LearningEngine`, `merchant_index`, rule migration (`_migrate_rules`).
- Depends on: `ConfigManager` for paths and limits.
- Used by: `BillCategorizer`; GUI edit flow calls `learn_from_decision(..., update_existing=True)` via `self.categorizer` reference.

**Infrastructure (I/O & Config):**
- Purpose: External data read/write and configuration.
- Location: `data_loader.py`, `data_exporter.py`, `config.py`
- Contains: pandas I/O, column standardization, CSV export naming.
- Depends on: `ConfigManager`; stdlib + pandas/openpyxl.
- Used by: `BillCategorizer`, `main.py`.

## Data Flow

### Primary Request Path

1. **Startup** — `main.py` calls `_setup_utf8_encoding()`, imports modules, builds `ConfigManager` → `DataLoader` → `LearningEngine` → UI → `DataExporter` → `BillCategorizer` (`main.py:94-128`).
2. **Source & file selection** — `BillCategorizer.run()` calls `ui.select_bill_source()` then `data_loader.find_excel_files()` + `ui.display_file_list()` (`categorizer.py:47-56`).
3. **Load & normalize** — `data_loader.load_excel_file(path, source)` returns standardized DataFrame with columns `交易时间`, `交易对方`, `商品`, `收/支`, `金额(元)`, `处理后的金额` (`data_loader.py:24-71`, `_standardize_to_wechat_format`).
4. **Person mode** — `ui.select_person_mode()` returns fixed person or per-transaction mode (`categorizer.py:96-107`).
5. **Per-transaction classify** — for each row: `learning_engine.get_suggestions()` → optional auto-apply on exact match → else `ui.display_classification_menu()` + `get_validated_input()` → `learning_engine.learn_from_decision()` (`categorizer.py:277-388`).
6. **Persist & export** — `learning_engine.save_data()` then `data_exporter.prepare_final_dataframe()` + `export_to_csv()` (`categorizer.py:141-153`, `data_exporter.py:16-147`).
7. **Results** — CLI: `exporter.display_preview()` + stats; GUI: `ui.show_results()` (`categorizer.py:390-409`).

### GUI Edit-Before-Export Flow

1. During classification, `gui_interface.add_classified_transaction()` populates Treeview and `classified_data`.
2. User double-click/right-click edits call `_edit_classified_transaction()` / `_delete_classified_transaction()`, mutating `current_processed_df`.
3. Before export, `BillCategorizer.run()` prefers `ui.current_processed_df` over the in-memory processed frame when present (`categorizer.py:146-150`).

### Internal Data Shape Transitions

```text
Raw bill (WeChat/Alipay CSV/XLSX)
  → standardized DataFrame (Chinese column names)
  → + columns [分类, 人员, 是否自动分类]
  → export DataFrame [Name, Category, Amount, Date, Person, Source, 是否自动分类, ...]
  → CSV file on disk
```

**State Management:**
- **Rules/history:** JSON files loaded at `LearningEngine.__init__`, saved after each bill batch via `save_data()`.
- **Session stats:** `BillCategorizer.stats` reset per bill in the outer loop.
- **GUI session state:** `GUIInterface.current_processed_df`, `classified_data`, `should_stop` flag for cooperative cancellation.
- **Config mutations:** New categories added at runtime via `config.set()` + `save_custom_config()` when user enters `[n]` new category (`categorizer.py:357-362`).

## Key Abstractions

**ConfigManager:**
- Purpose: Single source of truth for categories, people, file paths, display limits.
- Examples: `config.py`, consumed by every module.
- Pattern: Dot-path accessor (`get("categories.base_categories")`), deep-merge from `config.json`.

**UI Strategy (duck-typed interface):**
- Purpose: Swap CLI vs GUI without changing orchestrator logic.
- Examples: `user_interface.py`, `gui_interface.py`
- Pattern: Shared method names; GUI adds `show_results`, `add_classified_transaction`, `run`, `should_stop`. Detection: `hasattr(self.ui, 'show_results')`.

**Rule key (merchant|product):**
- Purpose: Granular learning beyond merchant-only keys.
- Examples: `learning_engine.py` — keys like `"美团|外卖"`, `"美团|"`, legacy plain merchant keys, optional `"regex:pattern"`.
- Pattern: Dict value is either `[category, count]` or `{category: count}` for multi-category rules.

**Standardized transaction row:**
- Purpose: Uniform processing regardless of bill source.
- Examples: Produced in `data_loader.py` `_standardize_to_wechat_format()`.
- Pattern: pandas Series/dict with Chinese canonical column names consumed by `categorizer._process_single_transaction()`.

## Entry Points

**Primary — `main.py`:**
- Location: `main.py`
- Triggers: `python main.py` or PyInstaller exe from `build.spec`
- Responsibilities: Module bootstrap, `--cli` flag, GUI thread orchestration, error dialogs.

**Legacy — `WeChatBillCategorizer.py`:**
- Location: `WeChatBillCategorizer.py`
- Triggers: Direct script execution (`if __name__ == "__main__"`)
- Responsibilities: Monolithic `OptimizedBillCategorizer` — self-contained rules, UI, export. Not wired into modular `main.py`.

**Analysis utility — `bill_analyzer.py`:**
- Location: `bill_analyzer.py`
- Triggers: Direct script execution
- Responsibilities: Read classified CSV, aggregate by year/month/quarter, matplotlib charts. Independent of classification pipeline.

**Test entry — `test_gui.py`:**
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

**What happens:** `categorizer.py` repeatedly checks `hasattr(self.ui, 'show_results')`, `hasattr(self.ui, 'should_stop')`, etc.
**Why it's wrong:** Fragile; adding a CLI feature with a similarly named method could mis-route behavior; scatters mode branching across orchestrator.
**Do this instead:** Introduce an explicit `is_gui: bool` or small `UIProtocol` / base class flag set at construction in `main.py`; keep mode checks in one place.

### GUI worker thread calling Tkinter without queue

**What happens:** Background thread calls `ui.add_classified_transaction()` and `root.update_idletasks()` directly.
**Why it's wrong:** Tkinter is not fully thread-safe; can cause intermittent UI corruption on some platforms.
**Do this instead:** Post UI updates via `root.after()` or the existing `task_queue` in `gui_interface.py` (`_process_queue`) for all cross-thread widget mutations.

### Legacy monolith coexisting with modular stack

**What happens:** `WeChatBillCategorizer.py` duplicates rules, loading, and classification logic separately from `learning_engine.py` / `categorizer.py`.
**Why it's wrong:** Bug fixes and feature additions (merchant|product keys, regex rules) may diverge; confuses which entry point is authoritative.
**Do this instead:** Treat `WeChatBillCategorizer.py` as deprecated; route all changes through modular modules. Remove or thin-wrap legacy file if no longer needed.

## Error Handling

**Strategy:** Broad try/except at boundaries with user-visible messages; inner failures often return `None` or empty structures rather than raising.

**Patterns:**
- File read failures: `data_loader.load_excel_file()` catches exceptions, prints traceback, returns `None` (`data_loader.py:66-71`).
- Import failures: `main.py` prints missing module list and `sys.exit(1)` (`main.py:68-78`).
- GUI init failure: falls back to `UserInterface` (`main.py:106-115`).
- Classification interrupt: user `q` returns `(None, None, False)`; partial DataFrame exported only if rows processed (`categorizer.py:209-212`, `227-275`).
- JSON load/save: try/except with console warnings in `LearningEngine` and `ConfigManager`.

## Cross-Cutting Concerns

**Logging:** `print()` with emoji-prefixed status messages throughout; no structured logging framework.
**Validation:** CLI via `UserInterface.get_validated_input()` input loops; GUI via button/modal constraints and `messagebox` for errors.
**Authentication:** Not applicable — local desktop tool, no network auth.

---

*Architecture analysis: 2026-06-08*
