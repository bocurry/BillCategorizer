---
phase: 03-gui-module-refactor
plan: 02
subsystem: ui
tags: [tkinter, gui-package, mixin, arch-05, classification-menu]

requires:
  - phase: 03-gui-module-refactor
    plan: 01
    provides: UI 性能优化（Label 复用、defer 批量、增量索引）
provides:
  - gui/ 包模块化 GUI（6 子模块 + re-export）
  - 分类菜单建议区增量更新、基础分类 Canvas 一次构建
  - from gui_interface import GUIInterface 对外 API 不变
affects:
  - Phase 4 总表合并 UI 钩子（可在 transaction_panel / results_panel 扩展）

key-files:
  created:
    - gui/__init__.py
    - gui/thread_bridge.py
    - gui/dialogs.py
    - gui/transaction_panel.py
    - gui/classified_list.py
    - gui/results_panel.py
    - gui/interface.py
  modified:
    - gui_interface.py

requirements-completed: [ARCH-05]

completed: 2026-06-08
---

# Phase 3 Plan 02: GUI 模块拆分 Summary

**将 ~1700 行 `gui_interface.py` 拆为 `gui/` 包，保持对外 API 与 Phase 1/03-01 行为；顺带实现手动分类菜单增量更新以减少闪烁。**

## Module Layout

| 模块 | 行数（约） | 职责 |
|------|-----------|------|
| `gui_interface.py` | 4 | 兼容 re-export |
| `gui/interface.py` | 141 | `GUIInterface` 组合 Mixin、`__init__`、welcome、run |
| `gui/thread_bridge.py` | 86 | `run_on_main_thread`、task_queue、show_error/info |
| `gui/dialogs.py` | 360 | 账单来源、文件、人员、继续处理等模态对话框 |
| `gui/transaction_panel.py` | 480 | 交易窗口、分类菜单（增量）、进度、defer 批量 |
| `gui/classified_list.py` | 266 | 已分类列表编辑/删除 |
| `gui/results_panel.py` | 156 | 结果预览与统计 |

## Accomplishments

- **ARCH-05：** 单文件均 ≤ 500 行；至少 4 个职责清晰子模块
- **API 不变：** `from gui_interface import GUIInterface` 与 `main.py` 无需改动
- **Phase 1 保留：** `run_on_main_thread`、窗口生命周期、多账单 reset 完整保留
- **Wave 1 保留：** Label/Text 复用、Treeview 增量索引、`progress_interval` 节流、自动分类 defer
- **手动分类 UX（Task 2 item 5）：** 建议区按钮 show/hide + rebind；基础分类 Canvas 首次构建后复用；n/s/q 操作按钮只建一次；idx 与 `get_validated_input(category_choice)` 一致

## Test Results

```
pytest test_gui.py test_phase1_integration.py -q
14 passed
python -c "from gui_interface import GUIInterface; print('OK')"  # OK
```

## Task 3 — 人工回归（Approved 2026-06-08）

用户确认通过：

1. `python main.py` — 处理账单（含手动分类）
2. 已分类列表编辑、继续第二单 — 正常
3. 手动分类菜单无闪烁
4. 已分类列表与进度同步（defer flush 修复后）

## Post-regression Fixes

- `dialogs.py`：`_select_unified_person` 嵌套模态 + grab_release
- `transaction_panel.py`：显示第 N 笔前 flush deferred，右侧列表与进度一致
- `test_gui.py`：+2 回归测试（16 passed）

## Notes

- Wave 2 子任务曾两次因连接中断；最终由恢复会话补全 `classified_list.py` 并验证通过
- `dialogs.py` 含人员选择逻辑，未再拆 `person_dialogs`（避免过度拆分）
