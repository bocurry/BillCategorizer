# Milestones

## v1.0 — BillCategorizer Refactor

**Shipped:** 2026-06-20  
**Tag:** `v1.0`

### Scope

- **Phases:** 5 (GUI thread safety, legacy cleanup, GUI refactor, testing/CI, docs/packaging)
- **Plans:** 4 formal plans (Phase 1 ×2, Phase 3 ×2)
- **Requirements:** 18/18 v1 complete

### Delivered

- GUI 主线程调度 + 多账单连续处理（无卡死）
- `gui/` 包拆分（6 模块），UI 性能优化
- 遗留单体删除、`.gitignore`、唯一入口 `main.py`
- 年度总表合并（`master_spreadsheet.py`）
- 35 pytest、CI 全绿（flake8 + pytest + PyInstaller）
- README + ARCHITECTURE.md 对齐代码

### Archives

- [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)

### Known deferred at close

- `.planning/codebase/` 仍为 2026-06-08 快照（见 STATE.md Deferred Items）
- v2：bill_analyzer 整理、special_types、graphify 知识图谱

### Key commits

- `b8be83d` — Phase 1/3 + 总表 + 打包
- `a9d78b0` — Phase 2/4/5 + CI 修复
- `9794181` — ARCHITECTURE.md 对齐
