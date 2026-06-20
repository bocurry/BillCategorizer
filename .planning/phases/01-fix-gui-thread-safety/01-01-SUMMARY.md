# Plan 01-01 Summary: GUIThreadBridge 基础设施

**Status:** Completed  
**Date:** 2026-06-15

## 完成项

- 实现 `GUIInterface.run_on_main_thread()` 与 `task_queue` 消费路径
- `_on_closing` / `_on_transaction_window_closing` 增加 `choice_event.set()` 唤醒 worker
- `main.py` 移除重复 `display_welcome()` 调用
- `categorizer.py` 经 `run_on_main_thread` 调度 `add_classified_transaction`，移除 `update_idletasks`
- `display_welcome` 增加 `_welcome_shown` 幂等标志
- GUI 首次运行经 `run_on_main_thread` 显示欢迎界面一次

## 修改文件

- `gui_interface.py`
- `main.py`
- `categorizer.py`
- `user_interface.py`（`show_error` / `show_info` CLI 回退）

## 验证

- `test_gui.py::test_run_on_main_thread_bridge`
- `grep` 确认 `main.py` 无 `display_welcome`、`categorizer.py` 无 `update_idletasks`
