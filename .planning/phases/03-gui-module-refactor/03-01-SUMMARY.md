---
phase: 03-gui-module-refactor
plan: 01
subsystem: ui
tags: [tkinter, treeview, performance, gui_interface, progress-throttling]

# Dependency graph
requires:
  - phase: 01-fix-gui-thread-safety
    provides: run_on_main_thread 主线程调度、交易窗口生命周期、多账单状态重置
provides:
  - 交易信息面板 Label/Text 复用（无逐笔 destroy/recreate）
  - 分类菜单 signature 缓存（结构未变时跳过重建）
  - Treeview tree_item_to_index 增量维护
  - progress_interval 进度节流与自动分类批量 Treeview 刷新
affects:
  - 03-02-PLAN.md（gui/ 包拆分将在优化后的刷新策略上重构）

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Widget reuse: 预创建 _txn_title_label / _txn_detail_text，config/delete+insert 更新"
    - "Menu cache: _classification_menu_signature 基于 suggestions + base_categories"
    - "Incremental index: 新条目 index=0，既有条目 pos+1，避免 O(n) 全量重建"
    - "Deferred batch: _deferred_classified + defer_classified_transaction / flush_deferred_classified_transactions"

key-files:
  created: []
  modified:
    - gui_interface.py
    - categorizer.py
    - config.json
    - test_gui.py
    - test_phase1_integration.py

key-decisions:
  - "自动分类路径使用 defer_classified_transaction 批量刷新 Treeview，手动分类保持即时 add_classified_transaction"
  - "分类菜单仅在 signature 变化时 destroy 重建，自动分类路径不调用 display_classification_menu"
  - "进度条与 Treeview 滚动均按 display.progress_interval（默认 10）节流"

patterns-established:
  - "Pattern: 面板更新优先复用 widget（config/text）而非 destroy children"
  - "Pattern: 结构性 UI（分类菜单）用 signature 缓存跳过无变化重建"
  - "Pattern: 集合索引增量维护，禁止每次插入后全量遍历重建映射"

requirements-completed: [UI-04]

# Metrics
duration: N/A (implementation pre-completed; documentation 2026-06-19)
completed: 2026-06-19
---

# Phase 3 Plan 01: UI 性能优化 Summary

**逐笔 UI 刷新改为 widget 复用、分类菜单 signature 缓存、Treeview 增量索引与 progress_interval 节流，大账单自动分类路径无全量 destroy/recreate 卡顿**

## Performance

- **Duration:** N/A（实现已完成；本文档记录于 2026-06-19）
- **Tasks:** 3/3
- **Files modified:** 5

## Accomplishments

- **交易信息面板复用：** `_display_transaction_impl` 预创建 `_txn_title_label` 与 `_txn_detail_text`，连续更新时子控件数量稳定（2 个），不再每笔 destroy 全部 children
- **分类菜单缓存：** `_classification_signature` + `_classification_menu_signature`；结构未变且已有子控件时跳过 destroy/rebuild；自动分类路径不调用 `display_classification_menu`
- **Treeview 增量索引：** `add_classified_transaction` 新条目 `tree_item_to_index[item_id]=0`，既有条目 `pos+1`，消除每次 O(n) 全量重建
- **进度节流与批量刷新：** 读取 `config display.progress_interval`（默认 10）；`_should_update_progress` 控制进度条更新；`defer_classified_transaction` / `flush_deferred_classified_transactions` 减少自动分类主线程调度次数
- **Phase 1 回归保持：** `run_on_main_thread` 包装不变；手动分类路径仍即时反馈

## Task Summary

| Task | 名称 | 状态 |
|------|------|------|
| 1 | 交易信息面板 Label 复用 | Done |
| 2 | 分类菜单缓存与增量 Treeview | Done |
| 3 | 进度节流与自动分类批量刷新 | Done |

## Test Results

```text
pytest test_gui.py test_phase1_integration.py -q
14 passed
```

**新增性能回归测试（3 项）：**

| 测试 | 验证点 |
|------|--------|
| `test_transaction_panel_reuses_widgets` | 连续两次 `_display_transaction_impl` 后 `transaction_info_frame` 子控件数不变（2） |
| `test_classified_tree_incremental_index` | 3 笔 `add_classified_transaction` 后 indices `[2,1,0]`，`tree_item_to_index` 与 `classified_data` 一致 |
| `test_progress_throttling` | `_should_update_progress` 在 idx=5/10/100 时 False/True/True |

**Phase 1 回归：** 原 11 项 + 新增 3 项 = 14 项全部通过。

## Files Created/Modified

- `gui_interface.py` — `_txn_title_label`/`_txn_detail_text` 复用；`_classification_menu_signature`；增量 `tree_item_to_index`；`_progress_interval`、`_should_update_progress`；`defer_classified_transaction` / `flush_deferred_classified_transactions`
- `categorizer.py` — 自动分类调用 `defer_classified_transaction`；手动分类前 `flush_deferred_classified_transactions`；循环结束最终 flush
- `config.json` — `display.progress_interval: 10` 确认/对齐
- `test_gui.py` — 3 项 UI 性能回归测试
- `test_phase1_integration.py` — 多账单集成测试适配批量刷新路径

## Decisions Made

- 自动分类与手动分类分流：自动走 defer 批量，手动走即时 `add_classified_transaction`（flush 先行）
- 分类菜单缓存采用完整 signature 比较，未实现增量追加按钮（categories 变化时仍全量重建）— 满足自动分类零重建路径
- 移除 `_display_transaction_impl` 末尾 `update_idletasks`，进度与面板更新合并节流

## Deviations from Plan

None - plan executed as specified. Implementation completed prior to this documentation pass.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Wave 2（03-02-PLAN）：** gui/ 包拆分可在当前性能优化基线上进行；刷新策略已收敛，拆分改动面更小
- **Blockers：** 无

## Self-Check: PASSED

- [x] `03-01-SUMMARY.md` created
- [x] Implementation files present (`gui_interface.py`, `categorizer.py`, `test_gui.py`)
- [x] Test suite: 14 passed (per verification)

---
*Phase: 03-gui-module-refactor*
*Completed: 2026-06-19*
