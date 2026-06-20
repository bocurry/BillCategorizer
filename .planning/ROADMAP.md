# Roadmap: BillCategorizer Refactor

**Created:** 2026-06-08
**Project Mode:** MVP (vertical slices)
**Granularity:** Standard (5 phases)

## Overview

大幅重构现有棕地代码库，优先修复 GUI 卡死 bug，再清理架构遗留、改进 UI 模块、建立测试与 CI 基线，最后统一文档与打包。

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Fix GUI Thread Safety | 修复多账单 GUI 卡死，恢复稳定可用 | BUG-01~03, ARCH-04, UI-01~03 | 5 |
| 2 | Legacy Cleanup | 统一入口，清除重复代码 | ARCH-01~03 | 4 |
| 3 | GUI Module Refactor | UI 流畅性 + 拆分 gui_interface | UI-04, ARCH-05 | 3 |
| 4 | Testing & CI | 建立测试基线与稳定 CI | TEST-01~04 | 4 |
| 5 | Docs & Packaging | 文档对齐、打包发布就绪 | DOC-01~04 | 4 |

---

### Phase 1: Fix GUI Thread Safety
**Goal:** 修复 GUI 模式下处理完第一个账单后偶发卡死的根因，使用户能稳定连续处理多个账单并正常关闭窗口
**Mode:** mvp
**Depends on:** None
**Requirements:** BUG-01, BUG-02, BUG-03, ARCH-04, UI-01, UI-02, UI-03
**Plans:** 2 plans
Plans:
- [x] 01-01-PLAN.md — GUIThreadBridge 基础设施、welcome 去重、关闭唤醒（Wave 1）
- [x] 01-02-PLAN.md — 对话框主线程迁移、窗口生命周期、测试与验收（Wave 2）
**Status:** Complete (2026-06-15, user approved)
**Success Criteria:**
1. GUI 模式下连续处理 3 个账单无卡死，「继续处理」对话框每次可响应
2. 处理过程中和完成后，用户可正常关闭主窗口退出程序
3. 所有 tkinter 调用经主线程调度，工作线程无直接 widget 操作
4. CLI 模式 (`python main.py --cli`) 回归测试通过，行为不变
5. 欢迎界面启动时仅显示一次

### Phase 2: Legacy Cleanup
**Goal:** 消除双轨代码和嵌套重复目录，确立 `main.py` 为唯一入口
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** ARCH-01, ARCH-02, ARCH-03
**Status:** Complete (2026-06-20)
**Success Criteria:**
1. `WeChatBillCategorizer.py` 已删除或标记弃用且逻辑已迁移验证
2. 嵌套 `BillCategorizer/` 目录已移除，仓库无重复源码
3. `python main.py` 是唯一文档化和打包的入口
4. 现有 `bill_rules_optimized.json` 规则库在重构后仍正常工作

### Phase 3: GUI Module Refactor
**Goal:** 优化逐笔 UI 流畅性并拆分 oversized `gui_interface.py`，改善可维护性与交互体验
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** UI-04, ARCH-05
**Plans:** 2 plans
Plans:
- [x] 03-01-PLAN.md — UI 性能优化（Label 复用、分类菜单缓存、增量 Treeview、进度节流）（Wave 1）
- [x] 03-02-PLAN.md — gui/ 包模块拆分 + 人工回归（Wave 2）
**Status:** Complete (2026-06-08, user approved)
**Success Criteria:**
1. 大账单（100+ 笔，80% 自动分类）处理时 UI 可响应，无明显逐笔卡顿
2. `gui_interface.py` 拆分为 3+ 职责清晰模块（gui/ 包），单文件不超过 500 行
3. Phase 1 线程安全模式在新模块结构中保持；分类编辑、结果预览回归正常

### Phase 4: Testing & CI
**Goal:** 建立自动化测试基线，修复并稳定 CI 流水线
**Mode:** mvp
**Depends on:** Phase 1, Phase 2
**Requirements:** TEST-01, TEST-02, TEST-03, TEST-04
**Status:** Complete (2026-06-20, CI green run #19)
**Success Criteria:**
1. `learning_engine.py` 和 `categorizer.py` 有单元测试且本地通过
2. GUI 多账单流程有冒烟测试（可 mock tkinter）
3. GitHub Actions CI 在 main 分支稳定绿灯
4. `.gitignore` 已添加，个人账单数据不会被 git 跟踪

### Phase 5: Docs & Packaging
**Goal:** 文档与真实代码对齐，PyInstaller 打包流程可用
**Mode:** mvp
**Depends on:** Phase 2, Phase 4
**Requirements:** DOC-01, DOC-02, DOC-03, DOC-04
**Status:** Complete (2026-06-20)
**Success Criteria:**
1. `README.md` 描述的结构、命令、依赖与代码一致
2. 不存在的模块引用（Notion 等）已从文档移除
3. `pyinstaller build.spec` 产出可运行的桌面可执行文件
4. 新贡献者可仅凭 README 完成环境搭建并运行程序

---

## Progress

| Phase | Status | Plans | Progress |
|-------|--------|-------|----------|
| 1 - Fix GUI Thread Safety | **Complete** | 2/2 | 100% |
| 2 - Legacy Cleanup | **Complete** | — | 100% |
| 3 - GUI Module Refactor | **Complete** | 2/2 | 100% |
| 4 - Testing & CI | **Complete** | — | 100% |
| 5 - Docs & Packaging | **Complete** | — | 100% |

---
*Roadmap created: 2026-06-08*
