# Requirements: BillCategorizer Refactor

**Defined:** 2026-06-08
**Core Value:** 用户能够稳定、流畅地完成账单导入→分类→导出流程；GUI 多账单处理不卡死

## v1 Requirements

### Bug Fixes

- [x] **BUG-01**: 用户可在 GUI 模式下连续处理多个账单，「继续处理」对话框始终可响应
- [x] **BUG-02**: 用户可在任意时刻正常关闭 GUI 主窗口，无需 Ctrl+C 强制退出
- [x] **BUG-03**: GUI 启动时欢迎界面不重复显示

### Architecture

- [ ] **ARCH-01**: 应用仅有唯一正式入口 `main.py`（文档与打包一致）
- [ ] **ARCH-02**: 遗留单体 `WeChatBillCategorizer.py` 已移除或明确弃用，逻辑无遗漏迁移
- [ ] **ARCH-03**: 嵌套重复目录 `BillCategorizer/` 已清理，消除双份源码混淆
- [x] **ARCH-04**: 所有 tkinter UI 调用通过主线程调度（`root.after` 或 task_queue），工作线程不直接操作 widget
- [x] **ARCH-05**: `gui_interface.py` 拆分为职责清晰的子模块（对话框、交易面板、分类列表等）

### User Interface

- [x] **UI-01**: 「继续处理下一个账单」流程在 GUI 中体验流畅，有明确的状态反馈
- [x] **UI-02**: 处理完成后结果预览与统计信息正常展示，不阻塞后续操作
- [x] **UI-03**: CLI 模式 (`--cli`) 行为与重构前保持一致，作为 GUI 的可靠备选
- [x] **UI-04**: 逐笔分类时 UI 流畅，自动分类路径无全量 destroy/recreate 卡顿

### Testing & CI

- [ ] **TEST-01**: 核心分类逻辑（`learning_engine.py`、`categorizer.py`）有单元测试覆盖
- [ ] **TEST-02**: GUI 多账单流程有自动化冒烟测试（可 mock tkinter）
- [ ] **TEST-03**: GitHub Actions CI 流水线（pytest + flake8 + PyInstaller）稳定通过
- [ ] **TEST-04**: 添加 `.gitignore`，排除个人账单数据、构建产物、venv

### Documentation & Packaging

- [ ] **DOC-01**: `README.md` 反映真实目录结构、运行方式（GUI/CLI）、依赖安装步骤
- [ ] **DOC-02**: `ARCHITECTURE.md` 与代码一致，或合并到 `.planning/codebase/` 引用
- [x] **DOC-03**: PyInstaller 打包流程文档化，`build.spec` 经验证可产出可执行文件
- [ ] **DOC-04**: 移除 README 中对不存在模块（如 `notion_integration.py`）的引用

## v2 Requirements

### Data & Analysis

- **DATA-01**: 将 `bill_analyzer.py` 整理为 `scripts/` 下的可选分析工具并文档化
- **DATA-02**: 修复导出月份与账单实际月份不一致的边缘情况

### Classification

- **CLAS-01**: 评估是否恢复 `special_types` 自动分类（转账/红包等）到模块化路径

## Out of Scope

| Feature | Reason |
|---------|--------|
| Notion 集成 | 模块不存在，非本次重构目标 |
| 新账单来源（银行 PDF 等） | 聚焦稳定性，非功能扩展 |
| Web/移动端 | 保持桌面单机定位 |
| 云同步/多用户 | 个人本地工具 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUG-01 | Phase 1 | Done |
| BUG-02 | Phase 1 | Done |
| BUG-03 | Phase 1 | Done |
| ARCH-04 | Phase 1 | Done |
| UI-01 | Phase 1 | Done |
| UI-02 | Phase 1 | Done |
| UI-03 | Phase 1 | Done |
| UI-04 | Phase 3 | Done |
| ARCH-01 | Phase 2 | Pending |
| ARCH-02 | Phase 2 | Pending |
| ARCH-03 | Phase 2 | Pending |
| ARCH-05 | Phase 3 | Done |
| TEST-01 | Phase 4 | Pending |
| TEST-02 | Phase 4 | Pending |
| TEST-03 | Phase 4 | Pending |
| TEST-04 | Phase 4 | Pending |
| DOC-01 | Phase 5 | Pending |
| DOC-02 | Phase 5 | Pending |
| DOC-03 | Phase 5 | Done |
| DOC-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-08*
*Last updated: 2026-06-19 — UI-04 marked Done (Phase 3 Wave 1)*
