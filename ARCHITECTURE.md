# BillCategorizer — 架构与流程文档

## 1. 项目概述

BillCategorizer 是面向个人/家庭使用的智能账单分类桌面工具，支持微信、支付宝账单导入与交互式分类。通过渐进式学习用户分类习惯，自动对交易记录分类，并导出结构化 CSV；可选合并到年度 Excel 总表。

### 主要特性

- 微信 / 支付宝账单（Excel / CSV），文件名可自动推断来源
- GUI（默认）与 CLI（`--cli`）双模式
- 规则库渐进学习：商户+商品组合键、正则规则、模糊匹配
- GUI 多账单连续处理（主线程调度 tkinter，工作线程分类）
- 导出至 `已分类/{year}/`，可选同步年度总表 xlsx
- PyInstaller 打包（`build.spec` → `dist/BillCategorizer/`）

**唯一入口：** `python main.py`（遗留单体 `WeChatBillCategorizer.py` 已移除）

---

## 2. 模块结构

```
BillCategorizer/
├── main.py                      # 入口：依赖注入、GUI/CLI 模式、后台线程
├── config.py                    # ConfigManager：默认配置 + config.json 合并
├── data_loader.py               # 账单发现、编码检测、格式标准化
├── learning_engine.py           # 规则库 / 历史 / 建议 / 学习
├── categorizer.py               # 分类流程编排（BillCategorizer）
├── user_interface.py            # CLI 交互
├── gui_interface.py             # GUI 兼容 re-export → gui.interface.GUIInterface
├── gui/                         # GUI 子模块（Mixin 组合）
│   ├── interface.py             # GUIInterface 主类
│   ├── thread_bridge.py         # 主线程调度（task_queue / run_on_main_thread）
│   ├── dialogs.py               # 来源、文件、人员、分类对话框
│   ├── transaction_panel.py     # 逐笔交易面板（Label 复用、菜单缓存）
│   ├── classified_list.py       # 已分类 Treeview 增量更新
│   └── results_panel.py         # 结果预览、总表同步、继续/退出
├── data_exporter.py             # 内部 DataFrame → 导出 CSV
├── master_spreadsheet.py        # 年度总表 xlsx 合并
├── app_paths.py                 # 开发/打包路径解析
├── bill_analyzer.py             # 可选：已分类 CSV 年度分析（独立脚本，需 matplotlib）
├── hooks/pyi_rth_billcategorizer.py  # PyInstaller runtime hook
├── build.spec                   # PyInstaller 规格（onedir）
├── scripts/build_exe.ps1        # Windows 打包脚本
├── config.json                  # 用户配置（可修改）
├── bill_rules_optimized.json    # 规则库（本地，gitignore）
└── bill_history.json            # 历史记录（本地，gitignore）
```

### 2.1 组件职责

| 组件 | 职责 | 文件 |
|------|------|------|
| 入口 / 引导 | UTF-8 修复、依赖检查、模块装配、GUI 线程 | `main.py` |
| 配置 | 点路径 `get()` / `set()`、文件路径 | `config.py` |
| 数据加载 | 解析微信/支付宝、标准化列、过滤无效行 | `data_loader.py` |
| 学习引擎 | 规则/历史持久化、建议、学习 | `learning_engine.py` |
| 分类编排 | 主循环、逐笔分类、统计、总表合并 | `categorizer.py` |
| CLI UI | 命令行提示与校验 | `user_interface.py` |
| GUI UI | Tkinter 对话框与面板，duck-type CLI 接口 | `gui/` + `gui_interface.py` |
| 导出 | 导出 schema、CSV 命名与目录 | `data_exporter.py` |
| 总表合并 | 按月份 sheet 追加、去重 | `master_spreadsheet.py` |
| 路径 | exe 目录 vs 捆绑资源 | `app_paths.py` |

---

## 3. 架构模式

- **扁平模块布局**：根目录 `.py` 文件，无 Python 包命名空间（`gui/` 为唯一子包）
- **依赖注入**：`BillCategorizer` 通过构造函数接收全部协作对象，不在内部实例化 loader/UI
- **UI 可替换**：`UserInterface` 与 `GUIInterface` 暴露相同方法面；编排器用 `hasattr(self.ui, 'show_results')` 识别 GUI
- **有状态持久化**：规则/历史为 JSON；会话内分类结果在 pandas DataFrame 列（`分类`、`人员`、`是否自动分类`）
- **GUI 线程模型**：Tkinter 主循环在主线程；`BillCategorizer.run()` 在 daemon 后台线程；跨线程 UI 经 `run_on_main_thread` + `task_queue`

---

## 4. 数据流程

### 4.1 主流程

```text
main.py 启动
  → ConfigManager / DataLoader / LearningEngine / UI / DataExporter
  → BillCategorizer.run()  [GUI: 后台线程]
       → 选择来源 → 选择文件 → resolve_bill_source（文件名可覆盖来源）
       → DataLoader 读取并标准化
       → 选择人员模式
       → 逐笔 _process_single_transaction
            → LearningEngine.get_suggestions
            → UI 获取分类（GUI: 主线程对话框）
            → LearningEngine.learn_from_decision
       → DataExporter 导出 CSV → 已分类/{year}/
       → 可选 _maybe_merge_to_master → master_spreadsheet
       → 显示结果；GUI 询问继续/退出
  → LearningEngine.save_data()
```

### 4.2 GUI 多账单循环

结果页「是，继续」→ `categorizer` 重置 GUI 状态 → 重新选择来源/文件，不重启进程。  
「否，退出」→ 设置 `should_stop`，结束外层 `while True`。

### 4.3 内部列名与导出列

**内部处理（中文列）：** `交易对方`、`商品`、`交易时间`、`金额(元)`、`收/支`、`分类`、`人员`、`是否自动分类`

**导出 CSV（英文列）：** `Name`、`Category`、`Amount`、`Date`、`Person`、`Source`、`是否自动分类`

---

## 5. 配置说明

### 5.1 config.json 要点

| 键 | 说明 |
|----|------|
| `files.rules_file` / `history_file` | 规则库与历史 JSON 路径 |
| `files.export_dir` | 导出目录模板，默认 `已分类/{year}` |
| `categories.*` | 来源、人员、基础分类列表 |
| `display.progress_interval` | CLI 进度间隔；GUI 自动分类批量刷新节流 |
| `master_spreadsheet.enabled` | 是否默认自动合并（默认 `false`） |
| `master_spreadsheet.path` | 总表路径，如 `已分类/{year}/{year}总表.xlsx` |
| `master_spreadsheet.sheet_naming` | Sheet 名模板，如 `{month}` → `4月` |
| `master_spreadsheet.dedupe_keys` | 去重键，默认 `Date` + `Amount` + `Name` |

GUI 可在结果页勾选「同步本单到总表」或「后续自动同步」，覆盖单次/会话行为。CLI 可用 `--merge-master`。

### 5.2 规则库格式

规则键支持多种形态：

- 组合键：`商户|商品` 或 `商户|`（无商品）
- 正则键：`regex:pattern`
- 遗留 plain 商户名（无 `|`）

值可为 `[分类, 次数]`、单值，或 `{分类: 次数}` 多分类字典。

---

## 6. 学习引擎（learning_engine.py）

### 6.1 建议优先级（get_suggestions）

1. **组合键精确/推荐匹配**：`商户|商品` 或 `商户|`
2. **正则匹配**：键以 `regex:` 开头
3. **模糊匹配**：商户名前 3 字符索引，仅针对无 `|` 的旧格式键

有商品名时组合键匹配标记为「精准匹配」；仅商户时标记为「推荐匹配」。

### 6.2 学习（learn_from_decision）

用户确认分类后更新规则计数并追加历史；GUI 编辑已分类记录时可 `update_existing=True` 修正规则。

### 6.3 持久化

启动时 `_load_data()`；每单处理结束 `save_data()`。规则超限时按使用次数裁剪。

---

## 7. 数据加载（data_loader.py）

- 递归搜索 `.xlsx` / `.xls` / `.csv`（含子目录）
- 多编码尝试（UTF-8、GBK 等）
- 支付宝 CSV 跳过说明行；过滤「不计收支」
- `_standardize_to_wechat_format()` 统一内部 schema
- `detect_bill_source_from_path()` / `resolve_bill_source()`：从文件名识别微信/支付宝，避免连续处理时来源错用

---

## 8. 导出与总表

### 8.1 data_exporter.py

- 文件名：`{用户名}-{月}月-{来源}-已分类账单.csv`
- 目录：`files.export_dir`（按账单 Date 众数解析 `{year}`）
- 金额：支出为负，收入为正；Date 为 `YYYY-MM-DD`

### 8.2 master_spreadsheet.py

- `MasterSpreadsheetMerger.merge_dataframe()`：打开/创建 xlsx，按月份 sheet 追加
- 去重：`Date` + `Amount` + `Name` 组合键
- 合并前可选备份；Excel 占用时返回友好错误（需关闭文件）

---

## 9. GUI 与 CLI

| 模式 | 界面模块 | 启动方式 |
|------|----------|----------|
| GUI | `gui_interface.GUIInterface` | `python main.py` |
| CLI | `user_interface.UserInterface` | `python main.py --cli` |

GUI 特性：

- 主窗口 `withdraw()`，无独立欢迎窗；对话框按需弹出
- 工作线程禁止直接操作 widget；经 `ThreadBridgeMixin`
- 结果页内「继续 / 退出」，避免阻塞式 `messagebox` 卡死

CLI 在 GUI 初始化失败时自动回退。

---

## 10. 打包与路径

### 10.1 app_paths.py

- `get_app_dir()`：可写目录（打包后为 exe 同目录）
- `get_bundle_dir()`：只读捆绑资源（`_MEIPASS`）
- `ensure_runtime_files()`：首次运行复制 JSON 模板到 exe 目录

### 10.2 build.spec

- 入口 `main.py`，`console=False`（窗口模式）
- `datas`：存在则捆绑 `config.json`、`bill_rules_optimized.json`、`bill_history.json`
- `hiddenimports`：含 `gui.*` 子模块
- Runtime hook：`hooks/pyi_rth_billcategorizer.py`

```bash
pyinstaller build.spec --clean --noconfirm
# 或 scripts/build_exe.ps1
```

---

## 11. 测试

| 文件 | 覆盖 |
|------|------|
| `test_learning_engine.py` | 建议、学习、正则规则 |
| `test_categorizer_core.py` | 总表开关、来源推断 |
| `test_master_spreadsheet.py` | 合并、去重、月份 |
| `test_gui.py` / `test_phase1_integration.py` | GUI 线程与多账单（CI 下 skip） |
| `test_app_paths.py` | 打包路径 |

```bash
pytest -v
```

CI（`.github/workflows/python-package-conda.yml`）：flake8 + pytest + PyInstaller（Linux / Windows）。

---

## 12. 扩展点

| 目标 | 修改位置 |
|------|----------|
| 新账单来源 | `data_loader.py`：加载器 + `_standardize_to_wechat_format` |
| 分类逻辑 | `learning_engine.py`：`get_suggestions` / `learn_from_decision` |
| GUI 交互 | `gui/` 对应 Mixin |
| 导出格式 | `data_exporter.py` |
| 总表策略 | `master_spreadsheet.py` + `config.json` |
| 年度分析 | `bill_analyzer.py`（独立运行，非主流程） |

---

## 13. 注意事项

1. **线程**：tkinter 必须在主线程；分类在 daemon 线程
2. **路径**：配置与 JSON 相对 `ConfigManager.config_dir`（默认项目根或 exe 目录）
3. **隐私**：账单 CSV、规则库、历史勿提交 git（见 `.gitignore`）
4. **总表**：合并前关闭 Excel，否则 Permission denied
5. **special_types**：模块化路径未恢复转账/红包自动分类（见 v2 需求 CLAS-01）

---

## 14. 相关文档

- 使用说明：`README.md`
- 重构规划：`.planning/ROADMAP.md`
- 代码库分析：`.planning/codebase/`

*文档对齐代码版本：v1.0 重构完成（2026-06）*
