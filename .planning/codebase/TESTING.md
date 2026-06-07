# Testing Patterns

**Analysis Date:** 2026-06-08

## Test Framework

**Runner:**
- pytest (declared in `environment.yml` under `pip:` dependencies; also installed in CI via `conda install pytest`)
- Config: Not detected — no `pytest.ini`, `pyproject.toml`, or `conftest.py`

**Assertion Library:**
- pytest built-in `assert` (implicit — current test has no explicit assertions)
- No `unittest`, `pytest-mock`, or `hypothesis` in dependencies

**Run Commands:**
```bash
pytest -v                    # Run all tests (from project root)
pytest -v test_gui.py        # Run GUI smoke test only
pytest -v -k test_gui        # Filter by test name

# With conda environment
conda env update --file environment.yml --name base
pytest -v
```

**Lint before test (matches CI):**
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```

## Test File Organization

**Location:**
- Root-level co-located: `test_gui.py` sits beside `main.py` and application modules
- No `tests/` directory
- Duplicate copy exists at `BillCategorizer/test_gui.py` (nested folder mirror — treat root `test_gui.py` as canonical)

**Naming:**
- Pattern: `test_<area>.py` with functions `test_<behavior>()`
- Only one test file in the active codebase: `test_gui.py`

**Structure:**
```
BillCategorizer/          # project root
├── test_gui.py           # sole automated test
├── main.py
├── categorizer.py
├── data_loader.py
├── learning_engine.py
├── gui_interface.py
├── user_interface.py
├── data_exporter.py
├── config.py
├── environment.yml       # pytest + flake8 deps
└── .github/workflows/python-package-conda.yml
```

## Test Structure

**Suite Organization:**
```python
# test_gui.py — actual pattern
import sys
import os
import pytest
import tkinter as tk
from tkinter import ttk, messagebox

@pytest.mark.skipif(
    os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true',
    reason="跳过CI环境中的GUI测试"
)
def test_gui():
    """测试GUI基本功能"""
    try:
        root = tk.Tk()
        # ... create window, label, button ...
        root.mainloop()
    except Exception as e:
        print(f"GUI测试失败: {e}")
        traceback.print_exc()
        if not os.environ.get('CI'):
            input("按回车键退出...")
```

**Patterns:**
- **Setup:** inline in test function — no fixtures, no `setUp`/`tearDown`
- **Teardown:** `root.destroy()` only in CI auto-close path; local run waits for user via `mainloop()`
- **Assertion:** none — test passes if no unhandled exception; manual visual verification locally
- **Docstrings:** Chinese description on test function
- **Dual entry:** `if __name__ == "__main__": test_gui()` for manual script execution

## Mocking

**Framework:** Not used — no `unittest.mock` or `pytest-mock` in codebase

**Patterns:**
- Not applicable — no mocking examples exist

**What to Mock (recommended for new tests):**
- `tkinter` dialogs and `mainloop()` in unit tests of `gui_interface.py`
- File I/O (`open`, `pd.read_csv`, `pd.read_excel`) when testing `data_loader.py` parsers
- `ConfigManager` with a temp directory for `learning_engine.py` rule persistence tests

**What NOT to Mock:**
- pandas DataFrame transformations when testing export logic — use small in-memory fixtures
- `LearningEngine.get_suggestions()` rule matching — use real JSON rule dicts

## Fixtures and Factories

**Test Data:**
- No shared fixtures in repo
- Production JSON files serve as implicit fixtures: `bill_rules_optimized.json`, `bill_history.json`, `config.json`
- Sample bill CSVs in `原始账单/` and classified output in `已分类/` — suitable for integration tests but not referenced by any test today

**Recommended fixture pattern for new tests:**
```python
# conftest.py (not present — create at project root if adding tests)
import pytest
import pandas as pd

@pytest.fixture
def sample_transaction_row():
    return {
        '交易对方': '测试商户',
        '商品': '测试商品',
        '交易时间': '2026-01-15 12:00:00',
        '金额(元)': '100.00',
        '收/支': '支出',
        '交易类型': '商户消费',
    }

@pytest.fixture
def minimal_config_manager(tmp_path):
    from config import ConfigManager
    return ConfigManager(config_dir=str(tmp_path))
```

**Location:**
- Create `conftest.py` at project root when introducing shared fixtures
- Keep sample CSV/JSON copies under a new `tests/fixtures/` directory — do not mutate committed `bill_rules_optimized.json` in tests

## Coverage

**Requirements:** None enforced — no coverage config, no coverage CI step, no minimum threshold

**View Coverage (if adding pytest-cov):**
```bash
pip install pytest-cov
pytest --cov=. --cov-report=term-missing --cov-ignore=bill,dist,BillCategorizer
```
Exclude `bill/` (venv), `dist/` (PyInstaller output), and nested `BillCategorizer/` duplicate when measuring.

## Test Types

**Unit Tests:**
- **Not present** for core modules
- Highest-value targets for new unit tests:
  - `learning_engine.py`: `_remove_numbers_from_product()`, `get_suggestions()`, `_migrate_rules()`
  - `data_loader.py`: `_find_alipay_data_start_line()`, `_convert_alipay_to_wechat_format()`, encoding fallback loops
  - `data_exporter.py`: `prepare_final_dataframe()`, `_clean_amount()`
  - `config.py`: `_merge_configs()`, `get()` dot-path access

**Integration Tests:**
- **Not present**
- Recommended flows:
  - Load sample CSV from `tests/fixtures/` → categorize with mocked UI → assert export CSV columns
  - Rule learn + save + reload round-trip in `learning_engine.py`

**E2E Tests:**
- `test_gui.py` is a manual smoke test for tkinter window display
- Skipped entirely in CI — see below
- Not true E2E of `BillCategorizer.run()` workflow

**Standalone manual scripts:**
- `test_gui.py` runnable as `python test_gui.py` for PyInstaller GUI diagnostics
- `bill_analyzer.py` — analysis tool, not covered by pytest

## CI Integration

**Pipeline:** `.github/workflows/python-package-conda.yml`

**Linux job (`build-linux`):**
1. `conda env update --file environment.yml`
2. Install Xvfb (virtual display for GUI)
3. flake8 (two-pass, same rules as local)
4. `pytest -v` with `CI=true` and `GITHUB_ACTIONS=true`
5. PyInstaller build (`build.spec`)

**Windows job (`build-windows`):**
1. `pip install pandas openpyxl pytest flake8 pyinstaller`
2. flake8 (same rules)
3. `pytest -v` with CI env vars
4. PyInstaller build

**CI test behavior:**
- `test_gui` is **always skipped** in CI due to `@pytest.mark.skipif` on `CI` / `GITHUB_ACTIONS`
- Effective CI test result: **0 tests run, 0 failures** — green build does not validate application logic
- Comment in workflow: `# 在CI环境中，GUI测试会被自动跳过`

**Environment variables affecting tests:**
| Variable | Effect |
|----------|--------|
| `CI=true` | Skips `test_gui` |
| `GITHUB_ACTIONS=true` | Skips `test_gui` |
| `DISPLAY=:99` | Set on Linux CI for Xvfb (unused while test skipped) |

## Common Patterns

**Async Testing:**
- Not used — synchronous pytest only
- GUI code uses `threading` — tests should not call `mainloop()` without timeout; use `root.after(ms, root.quit)` pattern from `test_gui.py` CI branch

**Error Testing (recommended — not yet in codebase):**
```python
def test_load_excel_file_returns_none_on_missing_file(config_manager):
    from data_loader import DataLoader
    loader = DataLoader(config_manager)
    result = loader.load_excel_file("/nonexistent/path.csv", "支付宝")
    assert result is None
```

**Parametrized parser tests (recommended):**
```python
@pytest.mark.parametrize("encoding", ["utf-8", "gbk", "gb2312"])
def test_alipay_csv_encoding_fallback(tmp_path, encoding):
    # write fixture file with encoding, assert DataFrame not None
    ...
```

**GUI test with timeout (recommended fix for CI):**
```python
@pytest.mark.skipif(os.environ.get('CI') == 'true', reason="...")
def test_gui_opens_and_closes():
    root = tk.Tk()
    root.after(500, root.destroy)
    root.mainloop()
    assert True
```

## Test Coverage Gaps

| Area | What's not tested | Files | Risk | Priority |
|------|-------------------|-------|------|----------|
| Rule matching | `get_suggestions()`, migration, index | `learning_engine.py` | Wrong auto-categories in production | **High** |
| Bill parsing | WeChat/Alipay CSV/Excel loaders, encoding | `data_loader.py` | Silent load failures on new export formats | **High** |
| Export format | Column mapping, amount sign, filename | `data_exporter.py` | Incorrect CSV output for Notion/downstream | **High** |
| Config merge | Nested override behavior | `config.py` | Misconfigured categories/limits | **Medium** |
| Categorizer flow | `_process_single_transaction`, batch loop | `categorizer.py` | Regression in core workflow | **High** |
| CLI input validation | `get_validated_input()` branches | `user_interface.py` | Invalid user input handling | **Medium** |
| GUI interface | Dialog flows, edit/delete classified rows | `gui_interface.py` | UI regressions undetected | **Medium** |
| Main orchestration | GUI fallback, threading, `--cli` flag | `main.py` | Startup failures after packaging | **Medium** |
| Bill analyzer | Annual report generation | `bill_analyzer.py` | Analysis script untested | **Low** |
| Legacy monolith | `WeChatBillCategorizer.py` | Legacy file | Dead code confusion | **Low** |

## Prescriptive Guidance for New Tests

1. **Place tests** in `tests/` directory (create it) or continue root `test_<module>.py` pattern — prefer `tests/` for scale
2. **Add `conftest.py`** with `tmp_path`-based `ConfigManager` and sample DataFrame fixtures
3. **Use pytest parametrize** for encoding/format variants in `data_loader.py`
4. **Do not rely on CI pytest** until skip is removed or real unit tests added — CI currently passes with zero executed tests
5. **Mock tkinter** in `gui_interface` tests; reserve `test_gui.py` for optional manual smoke only
6. **Run flake8** before pytest locally — matches CI gate
7. **Exclude** `bill/`, `dist/`, nested `BillCategorizer/` from test discovery:
   ```bash
   pytest -v --ignore=bill --ignore=dist --ignore=BillCategorizer
   ```

## Dependencies for Testing

From `environment.yml`:
```yaml
dependencies:
  - python=3.9
  - pandas
  - openpyxl
  - pip:
    - pytest
    - flake8
```

CI Windows additionally installs: `pandas openpyxl pytest flake8 pyinstaller`

Not in dependencies (consider adding for richer tests):
- `pytest-cov` — coverage reporting
- `pytest-mock` — mocking file/dialog interactions
- `pytest-timeout` — prevent hung GUI tests

---

*Testing analysis: 2026-06-08*
