# Phase 3 Research: GUI 性能与模块拆分

**Date:** 2026-06-15  
**Phase:** 03-gui-module-refactor

## 问题陈述

用户反馈：逐笔分类时界面明显卡顿。Phase 1 已修复线程安全与多账单卡死，但 UI 刷新策略仍是性能瓶颈。

## 根因（代码审查 2026-06-15）

| 位置 | 现状 | 影响 |
|------|------|------|
| `_display_transaction_impl` L767-796 | 每笔 destroy 全部 Label 并重建 | 高频布局抖动 |
| `_display_classification_menu_impl` L934+ | 手动分类时 destroy 整个按钮网格 | 大分类列表时极慢 |
| `add_classified_transaction` L1060-1067 | 每笔 O(n) 重算 `tree_item_to_index` | 账单越长越慢 |
| `_display_progress_impl` | 每笔调用（`progress_interval` 未用于 transaction 路径） | 多余刷新 |
| 自动分类路径 | 每笔仍完整 refresh transaction 面板 | 80%+ 自动时浪费 |

## 模块拆分边界（ARCH-05）

当前 `gui_interface.py` ~1687 行，建议拆为：

```
gui/
  __init__.py          # 导出 GUIInterface
  thread_bridge.py     # run_on_main_thread, task_queue, _widget_alive (~120行)
  dialogs.py           # 来源/文件/人员选择、ask_continue (~450行)
  transaction_panel.py # 交易窗口、分类菜单、已分类列表 (~550行)
  results_panel.py     # show_results、预览刷新 (~180行)
  interface.py         # GUIInterface 组合入口、welcome、run (~250行)
```

`GUIInterface` 保持对外 API 不变（duck typing 与 `categorizer.py` 兼容）。

## 决策

1. **Wave 1 先做性能**（用户可感知），Wave 2 再拆分模块（可维护性）
2. 性能优化不破坏 Phase 1 线程安全契约（所有 UI 仍在主线程）
3. `progress_interval` 从 config 读取，默认 10，应用于 progress + auto-classify 批量刷新

## 参考

- Phase 1 SUMMARY: run_on_main_thread 模式必须保留
- `config.json` display.progress_interval: 10
- 现有测试: test_gui.py + test_phase1_integration.py（11 passed）
