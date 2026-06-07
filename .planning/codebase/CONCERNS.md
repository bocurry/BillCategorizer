# Codebase Concerns

**Analysis Date:** 2026-06-08

## Tech Debt

**Legacy monolith vs modular architecture:**
- Issue: Two parallel implementations coexist. `WeChatBillCategorizer.py` (~727 lines) is a self-contained CLI monolith (`OptimizedBillCategorizer`) with its own `main()`. The active entry point is `main.py`, which wires modular files (`config.py`, `data_loader.py`, `learning_engine.py`, `categorizer.py`, `user_interface.py`, `gui_interface.py`, `data_exporter.py`). Logic is duplicated and has diverged.
- Files: `WeChatBillCategorizer.py`, `main.py`, `categorizer.py`, `learning_engine.py`
- Impact: Bug fixes and feature work may land in one copy only. Running `python WeChatBillCategorizer.py` vs `python main.py` produces different behavior (see Known Bugs). PyInstaller builds from `main.py` (`build.spec`), so the monolith is dead code for packaged releases but still confusing for developers.
- Fix approach: Deprecate or delete `WeChatBillCategorizer.py` after verifying parity, or extract any unique logic into shared modules. Add a one-line comment at the top of the monolith pointing to `main.py`.

**Nested duplicate `BillCategorizer/` directory:**
- Issue: A second copy of the project lives at `BillCategorizer/` (includes its own `.git`, `main.py`, `gui_interface.py`, `learning_engine.py`, etc.). The nested `BillCategorizer/learning_engine.py` still uses `"精确匹配"` strings while the root `learning_engine.py` uses `"精准匹配"` and merchant|product composite keys — evidence the nested tree is stale.
- Files: `BillCategorizer/learning_engine.py`, `BillCategorizer/gui_interface.py`, `BillCategorizer/WeChatBillCategorizer.py`, `BillCategorizer/asd.py`
- Impact: Editors and searches hit the wrong file. Accidental edits to the nested copy have no effect on the running app.
- Fix approach: Remove the nested clone from the working tree or convert to a documented submodule with a single source of truth at repo root.

**GUI thread-safety architecture (root cause of post-bill freeze):**
- Issue: `main.py` runs `categorizer.run()` on a daemon background thread while tkinter `mainloop()` runs on the main thread. All GUI methods in `gui_interface.py` are invoked directly from the worker thread. A `task_queue` and `_process_queue()` exist but nothing enqueues UI work — the queue is unused scaffolding.
- Files: `main.py` (lines 134–163), `gui_interface.py` (lines 50–51, 147–158, 1455–1464), `categorizer.py` (entire `run()` loop)
- Impact: tkinter is not thread-safe. Cross-thread widget creation, `grab_set()`, `wait_window()`, and `messagebox` calls cause intermittent deadlocks. Symptoms match reported behavior: first bill may complete, then "继续处理" / window close hangs until Ctrl+C.
- Fix approach: Marshal every UI call to the main thread via `root.after(0, ...)` or the existing `task_queue`. Pattern: worker thread sets a `threading.Event` after scheduling dialog on main thread; never call `Toplevel`, `grab_set`, or `wait_window` from the categorizer thread. Consider running categorizer logic on main thread with `after`-chunked processing for auto-classified rows.

**Oversized GUI module:**
- Issue: `gui_interface.py` is ~1527 lines mixing welcome flow, modal dialogs, transaction window, classified-list CRUD, result preview, and learning-engine callbacks.
- Files: `gui_interface.py`
- Impact: High regression risk when fixing the thread bug or adding features. Classified-list index bookkeeping (`classified_data` reverse order vs `processed_df` forward index) is hard to reason about.
- Fix approach: Split into focused modules (dialogs, transaction panel, classified list editor) after fixing thread model.

**README and documentation drift:**
- Issue: `README.md` describes a non-existent layout and outdated workflow. `ARCHITECTURE.md` at repo root is accurate but not linked from README.
- Files: `README.md`, `ARCHITECTURE.md`
- Impact: New contributors follow wrong paths, wrong filenames, and miss GUI/CLI modes.
- Fix approach: Rewrite README to match actual tree (see README Drift section below).

**Orphan / scratch artifacts:**
- Issue: `bill_analyzer.py` (~785 lines) is a standalone analysis tool not wired into `main.py`. `BillCategorizer/asd.py` is a one-off JSON formatter. `notion_integration.py` is referenced in README and `config.json` but does not exist.
- Files: `bill_analyzer.py`, `BillCategorizer/asd.py`, `config.json`, `README.md`
- Impact: Documentation promises features that are absent; repo clutter.
- Fix approach: Move analysis script to `scripts/` or document as optional tool; remove `asd.py`; drop Notion references or implement the module.

**No `.gitignore`:**
- Issue: No root `.gitignore` detected. Personal bill CSVs, classified outputs, `bill_history.json`, `dist/`, local venv `bill/`, and debug logs appear in the workspace.
- Files: `原始账单/`, `已分类/`, `分类明细/`, `bill_history.json`, `dist/`, `bill/`, `.cursor/debug.log`
- Impact: Risk of committing PII and bloating the repository; CI flake8 may scan vendored `bill/` packages.
- Fix approach: Add `.gitignore` for data dirs, build artifacts, venvs, and `*.json` history files; keep `config.json` template separate from personal overrides.

## Known Bugs

**GUI hang after first bill / continue flow freeze:**
- Symptoms: After completing one bill in GUI mode, the "是否继续处理下一个账单？" dialog may not respond; main window cannot close cleanly; user must Ctrl+C to exit.
- Files: `main.py`, `gui_interface.py` (`ask_continue_processing`, `show_results`, `_show_modal_dialog`), `categorizer.py` (post-export loop at line 163)
- Trigger: Run `python main.py` (default GUI), process one full bill through export, then interact with continue dialog or try to close the window.
- Workaround: Use CLI mode (`python main.py --cli`) for batch processing; or process only one bill per launch.
- Root cause: Background thread invokes tkinter modal dialogs (`grab_set` + `wait_window` + `choice_event.wait`) and `messagebox.showinfo` in `show_results` (line 1156) off the main thread. After first bill, `transaction_window` may still be open when `ask_continue_processing` grabs focus — compounding grab-order deadlocks.

**`display_welcome` called twice in GUI mode:**
- Symptoms: Welcome UI may flash or re-render unexpectedly on startup.
- Files: `main.py` (line 137), `categorizer.py` (lines 36–38)
- Trigger: GUI startup path.
- Workaround: None user-facing; cosmetic.
- Fix approach: Call `display_welcome` in only one place.

**Export month may not match bill period:**
- Symptoms: Output filename uses month from first row after descending date sort, not the dominant month or user-selected period.
- Files: `data_exporter.py` (lines 114–131)
- Trigger: Multi-month input files or bills spanning month boundaries.
- Workaround: Manually rename output CSV.

**Monolith auto-classification via `special_types` removed in modular path:**
- Symptoms: `python WeChatBillCategorizer.py` auto-maps 转账/微信红包/收付款 to 人情往来; `python main.py` does not (ARCHITECTURE.md notes removal).
- Files: `WeChatBillCategorizer.py` (lines 66–70, 351–355), `learning_engine.py`, `config.json` (`special_types` absent)
- Trigger: Compare same bill across entry points.
- Workaround: Use one entry point consistently.

**Rule-key format mismatch (monolith vs modular):**
- Symptoms: Monolith matches rules by merchant string only (`merchant_str in self.rules`). Modular `learning_engine.py` uses composite keys `merchant|product` with migration logic — shared `bill_rules_optimized.json` may behave differently per entry point.
- Files: `WeChatBillCategorizer.py`, `learning_engine.py`, `bill_rules_optimized.json`
- Trigger: Rules created by one implementation read by the other.
- Workaround: Only run `main.py`; do not use monolith on the same rules file.

## Security Considerations

**Personal financial data in repository tree:**
- Risk: Real names and transaction data in `原始账单/`, `已分类/`, `分类明细/`, and `bill_history.json`. `config.json` lists real people names (`袁程波`, `杜雨秦`).
- Files: `原始账单/`, `已分类/`, `分类明细/`, `bill_history.json`, `config.json`
- Current mitigation: None (no `.gitignore`).
- Recommendations: Add `.gitignore`; rotate/remove committed PII from git history if already pushed; use `config.local.json` for personal names; never commit raw bills.

**No secrets management:**
- Risk: `config.json` references `notion_config_file` for future API integration; no encryption or env-var pattern exists.
- Files: `config.py`, `config.json`
- Current mitigation: Notion module not implemented.
- Recommendations: When adding integrations, load tokens from environment variables; add `notion_config.json` to `.gitignore`.

## Performance Bottlenecks

**Per-row GUI refresh during classification:**
- Problem: Each transaction calls `root.update_idletasks()` and rebuilds classification widgets in `display_classification_menu`.
- Files: `categorizer.py` (line 223), `gui_interface.py` (`display_classification_menu`, `display_transaction`)
- Cause: Full widget destroy/recreate per row on a large bill.
- Improvement path: Reuse widget tree; batch auto-classified rows without opening classification UI (partially done for exact match).

**Synchronous pandas iteration:**
- Problem: `for idx, row in df.iterrows()` in `categorizer.py` is slow for thousands of rows.
- Files: `categorizer.py` (line 193)
- Cause: `iterrows()` overhead.
- Improvement path: Use `itertuples()` or vectorized pre-filter for auto-classified rows.

**Rule/history file rewrite on every save:**
- Problem: `learning_engine.save_data()` rewrites full JSON files; GUI edit path calls save per edit (`gui_interface.py` line 1387).
- Files: `learning_engine.py`, `gui_interface.py`
- Cause: No incremental or debounced persistence.
- Improvement path: Debounce saves; append-only history with periodic compaction.

## Fragile Areas

**`classified_data` index ↔ `current_processed_df` synchronization:**
- Files: `gui_interface.py` (`add_classified_transaction`, `_edit_classified_transaction`, `_delete_classified_transaction`), `categorizer.py` (`_process_transactions` merge logic, lines 234–265)
- Why fragile: `classified_data` is stored in reverse display order; `index` field is recomputed with `len - 1 - i`. Edit/delete/merge paths have multiple fallback branches (`loc` vs `iloc` vs reset_index).
- Safe modification: Add integration tests for edit-then-export and delete-then-export; always update through a single sync function.
- Test coverage: None for this path.

**`learning_engine` rule migration:**
- Files: `learning_engine.py` (`_migrate_rules`, `_load_data`, composite `merchant|product` keys)
- Why fragile: One-time migration mutates `bill_rules_optimized.json` on load; mixed old/new key formats in the same file.
- Safe modification: Backup rules file before migration; add unit tests for migration cases.
- Test coverage: None.

**Modal dialog + `threading.Event` pattern:**
- Files: `gui_interface.py` (`_show_modal_dialog`, `get_validated_input`, all `select_*` methods)
- Why fragile: Combines `wait_window()` with `choice_event.wait()`; unsafe when called off main thread.
- Safe modification: Fix thread model first; then simplify to callback-based or `async` queue without double-wait.
- Test coverage: `test_gui.py` only checks basic tk window creation.

**PyInstaller GUI packaging:**
- Files: `build.spec`, `main.py`, `gui_interface.py`
- Why fragile: Threading + tkinter + `console=False` build hides stderr; failures surface as silent hangs.
- Safe modification: Test packaged exe through full bill + continue flow on Windows.
- Test coverage: CI builds artifacts but does not run end-to-end GUI flow (`test_gui.py` skipped in CI).

## Scaling Limits

**Rule and history caps:**
- Current capacity: 50,000 rules, 5,000 history entries (`config.json` limits).
- Limit: In-memory dict + JSON full rewrite; large files slow startup and save.
- Scaling path: SQLite or partitioned storage; lazy index build.

**Single-user desktop assumption:**
- Current capacity: One process, local filesystem, no concurrent access.
- Limit: Two instances writing `bill_rules_optimized.json` can corrupt data.
- Scaling path: File locking or single-instance mutex.

## Dependencies at Risk

**Pinned loosely via conda/pip only:**
- Risk: `environment.yml` pins `python=3.9` but not pandas/openpyxl versions; `README.md` says `pip install pandas openpyxl` with no versions.
- Impact: Non-reproducible installs; CI uses Python 3.10 while conda env says 3.9.
- Migration plan: Pin versions in `environment.yml` and a `requirements.txt`; align CI Python version with local conda.

**tkinter (stdlib) on non-Windows CI:**
- Risk: Linux CI skips real GUI tests; Windows-specific grab/focus issues (`focus_force`) may not be caught.
- Impact: GUI regressions ship to Windows users.
- Migration plan: Add Windows CI job or headless tk interaction tests for dialog flow.

## Missing Critical Features

**Notion integration:**
- Problem: Documented in `README.md` and `config.json` but `notion_integration.py` does not exist and `main.py` does not import it.
- Blocks: Automated export to Notion.

**Batch continue flow in GUI:**
- Problem: Multi-bill loop exists in `categorizer.run()` but GUI thread bug prevents reliable second iteration.
- Blocks: Processing multiple monthly bills in one GUI session.

**Bank / cash data loaders:**
- Problem: `data_loader.py` routes non-WeChat/Alipay sources to generic loaders; quality unknown.
- Blocks: Reliable multi-source workflow advertised in `config.json` bill_sources.

## Test Coverage Gaps

**Categorizer core loop:**
- What's not tested: File load, suggestion logic, export, continue loop, auto vs manual classification stats.
- Files: `categorizer.py`, `learning_engine.py`, `data_loader.py`, `data_exporter.py`
- Risk: Regressions in classification and export go unnoticed.
- Priority: High

**GUI multi-bill and continue dialog:**
- What's not tested: `ask_continue_processing`, `show_results`, thread-safe dialog marshalling.
- Files: `gui_interface.py`, `main.py`
- Risk: Known freeze bug can reappear after fixes.
- Priority: High

**Classified-list edit/delete/export consistency:**
- What's not tested: Double-click edit, delete row, export after edit.
- Files: `gui_interface.py`
- Risk: Wrong categories in exported CSV after GUI edits.
- Priority: Medium

**Only existing test:**
- Files: `test_gui.py` — smoke test creating a tk window; skipped when `CI=true` / `GITHUB_ACTIONS=true`.
- Risk: CI provides almost no functional coverage.

## README Drift (Detailed)

| README claim | Actual state |
|--------------|--------------|
| Directory `wechat_bill_categorizer/` | Flat layout at repo root; no such subdirectory |
| Entry `python main.py` only | Correct, but also `python main.py --cli` exists undocumented |
| File `wechat_categorizer.py` | Does not exist; legacy name is `WeChatBillCategorizer.py` |
| Lists `notion_integration.py` | File missing |
| Implies WeChat-only tool | Supports 支付宝, 银行, 现金, 其他 via `data_loader.py` |
| `pip install pandas openpyxl` | `environment.yml` exists for conda; no `requirements.txt` |
| "修改 UI → `user_interface.py`" | GUI mode uses `gui_interface.py`; CLI uses `user_interface.py` |
| No mention of `gui_interface.py`, `bill_analyzer.py`, `WeChatBillCategorizer.py` | All present and relevant to understanding the codebase |
| No mention of `ARCHITECTURE.md` | Accurate architecture doc exists at repo root |

**Prescriptive fix for README:** Document actual module table from `ARCHITECTURE.md` §2.1, both run modes (`python main.py` / `--cli`), conda setup via `environment.yml`, and mark `WeChatBillCategorizer.py` as legacy.

---

*Concerns audit: 2026-06-08*
