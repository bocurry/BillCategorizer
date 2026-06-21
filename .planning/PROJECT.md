# BillCategorizer

## What This Is

BillCategorizer 是面向个人/家庭的智能账单分类桌面工具，支持微信、支付宝账单导入与交互式分类。通过渐进式学习分类习惯自动分类，导出结构化 CSV，并可选合并到年度 Excel 总表。

## Core Value

用户能够稳定、流畅地完成「导入账单 → 分类（自动+手动）→ 导出已分类 CSV」；GUI 多账单处理不卡死、可正常关闭。

## Current State (v1.0 — shipped 2026-06-20)

| 项 | 状态 |
|----|------|
| 入口 | `python main.py`（GUI）/ `--cli` |
| GUI | `gui/` 包，主线程桥接，多账单继续/退出 |
| 测试 | 35 pytest；CI 全绿 |
| 打包 | `pyinstaller build.spec` → `dist/BillCategorizer/` |
| 文档 | `README.md`、`ARCHITECTURE.md` 已对齐 |
| 遗留代码 | `WeChatBillCategorizer.py` 已删除 |

**扩展（v1 会话内交付，非原 ROADMAP）：** `master_spreadsheet.py` 年度总表合并

## Requirements

### Validated (v1.0)

- ✓ GUI 多账单不卡死、可关闭 — v1.0 Phase 1
- ✓ tkinter 主线程调度 — v1.0 Phase 1
- ✓ `gui/` 包拆分 + UI 性能 — v1.0 Phase 3
- ✓ 遗留清理、唯一入口 — v1.0 Phase 2
- ✓ 单元测试 + CI 绿灯 — v1.0 Phase 4
- ✓ README / ARCHITECTURE / 打包 — v1.0 Phase 5
- ✓ `.gitignore` 保护个人账单 — v1.0 Phase 4
- ✓ 微信/支付宝、规则学习、CSV 导出 — existing

### Active (v2 候选)

- [ ] 将 `bill_analyzer.py` 迁入 `scripts/` 并文档化（DATA-01）
- [ ] 评估恢复 `special_types` 自动分类（CLAS-01）
- [ ] 刷新 `.planning/codebase/` 或启用 graphify 知识图谱
- [ ] 导出月份边缘情况（DATA-02）

### Out of Scope

- Notion 集成
- 新账单来源（银行 PDF 等）
- Web/移动端、云同步

## Context

**技术栈：** Python 3.9+、pandas、openpyxl、tkinter、PyInstaller、pytest、flake8、Conda

**仓库：** `git@github.com:bocurry/BillCategorizer.git`

**运行产物：** 单账单 CSV → `已分类/{year}/`；可选总表 → `已分类/{year}/{year}总表.xlsx`

## Constraints

- 保持 Python + tkinter + pandas
- `bill_rules_optimized.json` 向后兼容
- 个人账单不得提交 git
- 打包与文档统一指向 `main.py`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GUI 线程：主线程调度 | 工作线程直接 tkinter 导致卡死 | ✓ Phase 1 |
| 先 Phase 3 后 Phase 2 | 用户优先体验 | ✓ 已执行 |
| 删除遗留单体 | 双轨代码混淆 | ✓ Phase 2 |
| 总表默认 enabled: false | 避免误覆盖 Excel | ✓ 用户验证 |
| 垂直 MVP 阶段 | 每阶段可交付 | ✓ v1.0 完成 |

## Next Milestone Goals

运行 `/gsd-new-milestone` 启动 v2.0 规划。建议优先：

1. 刷新 planning/codebase 文档或 graphify
2. v2 功能（bill_analyzer、special_types）

---
*Last updated: 2026-06-20 after v1.0 milestone*
