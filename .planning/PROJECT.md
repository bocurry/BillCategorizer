# BillCategorizer

## What This Is

BillCategorizer 是一个面向个人/家庭使用的智能账单分类桌面工具，支持微信、支付宝账单的导入与交互式分类。通过渐进式学习用户的分类习惯，自动对交易记录进行分类，并导出结构化 CSV。本次工作是对现有棕地代码库的大幅重构，而非从零新建。

## Core Value

用户能够稳定、流畅地完成「导入账单 → 分类（自动+手动）→ 导出已分类 CSV」的完整流程；GUI 模式下处理多个账单时不卡死、可正常关闭窗口。

## Requirements

### Validated

- ✓ 支持微信、支付宝账单（Excel/CSV）读取与格式统一 — existing
- ✓ 渐进式学习分类规则（`learning_engine.py` + `bill_rules_optimized.json`）— existing
- ✓ CLI 与 GUI 双模式运行（`main.py --cli` / 默认 GUI）— existing
- ✓ 导出命名格式 `用户名-月份-来源-已分类账单.csv` — existing
- ✓ 批处理多个账单文件（循环处理）— existing（CLI 稳定；GUI 有已知缺陷）
- ✓ PyInstaller 打包入口为 `main.py` — existing

### Active

- [ ] 修复 GUI 处理完第一个账单后偶发卡死、无法继续/关闭的 bug
- [ ] 将 GUI 所有 UI 调用调度到主线程（修复 tkinter 线程安全问题）
- [ ] 清理遗留单体 `WeChatBillCategorizer.py`，统一为模块化架构
- [ ] 解决嵌套重复目录 `BillCategorizer/` 造成的混淆
- [ ] 拆分 oversized `gui_interface.py`，改进交互体验
- [ ] 补充核心逻辑与 GUI 多账单流程的自动化测试
- [ ] 修复并稳定 CI 流水线（pytest + flake8 + PyInstaller）
- [ ] 更新 README 与文档，使其与真实目录结构一致
- [ ] 添加 `.gitignore`，避免个人账单数据入库
- [ ] 改进 PyInstaller 打包与发布流程

### Out of Scope

- Notion 集成 — README 曾提及但模块不存在，本次不实现
- 新增账单来源（银行 PDF 等）— 聚焦稳定性与架构，非功能扩展
- Web 版或移动端 — 保持桌面单机应用定位
- 云同步或多用户 — 个人本地工具，无此需求

## Context

**当前技术栈：** Python 3.9、pandas、openpyxl、tkinter、PyInstaller、pytest、flake8、Conda。

**代码库现状（2026-06-08 映射）：**
- 活跃入口：`main.py` → 模块化组件（`categorizer.py`、`gui_interface.py` 等）
- 遗留单体：`WeChatBillCategorizer.py`（~727 行），与模块化实现逻辑已分叉
- 嵌套重复：`BillCategorizer/` 子目录含过期副本
- GUI 架构缺陷：`categorizer.run()` 在后台线程执行，但 `gui_interface.py` 直接从工作线程调用 tkinter，导致「继续处理」对话框和窗口关闭偶发死锁
- 测试薄弱：仅 `test_gui.py` 冒烟测试，无核心逻辑单测
- 文档漂移：根目录 `README.md` 描述的结构与实际不符；`ARCHITECTURE.md` 较准确
- 无 `.gitignore`：个人账单 CSV/JSON 可能误入版本库

**用户报告的关键 bug：** GUI 模式处理完第一个账单后，「继续处理」有概率卡住，窗口无法关闭，只能在命令行 Ctrl+C / Ctrl+Z 强制退出。

**仓库：** `git@github.com:bocurry/BillCategorizer.git`

## Constraints

- **Tech stack**: 保持 Python + tkinter + pandas — 用户本地 Conda 环境已配置，避免引入重型新框架
- **Compatibility**: 现有 `bill_rules_optimized.json` 规则库需向后兼容或提供迁移
- **Data privacy**: 个人账单数据不得提交到 git
- **Entry point**: 打包与文档统一指向 `main.py`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 先运行 `/gsd-map-codebase` 再初始化项目 | 棕地项目，需基于真实架构做规划 | ✓ 已完成（7 份文档） |
| 大幅重构（允许重新设计架构） | 用户明确选择 major 深度 | — Pending |
| 垂直 MVP 切片组织阶段 | 每阶段交付可用的端到端改进 | — Pending |
| 跳过领域调研 | 用户对项目熟悉，问题明确 | ✓ 已确认 |
| GUI 线程模型：所有 UI 调度到主线程 | CONCERNS.md 确认根因 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-08 after initialization*
