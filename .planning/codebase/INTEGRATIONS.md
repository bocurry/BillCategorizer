# External Integrations

**Analysis Date:** 2026-06-08

## APIs & External Services

**账单数据来源（离线文件，非实时 API）:**
- 微信支付 — 用户手动导出 Excel/CSV，由 `data_loader.py` 解析（`_load_wechat_excel`、`_load_wechat_csv`）
  - SDK/Client: 无；使用 `pandas` + `openpyxl` 本地读取
  - Auth: 不适用（文件已导出到本地）
- 支付宝 — 用户手动导出 Excel/CSV，由 `data_loader.py` 解析（`_load_alipay_excel`、`_load_alipay_csv`）
  - SDK/Client: 无；使用 `pandas` + `openpyxl` 本地读取
  - Auth: 不适用
- 银行/现金/其他 — 通用 Excel/CSV 加载路径（`_load_generic_excel`、`_load_generic_csv`）

**计划但未实现的集成:**
- Notion — `README.md` 提及 `notion_integration.py`；`config.py` / `config.json` 预留 `notion_config_file: notion_config.json`
  - SDK/Client: 未检测到
  - Auth: 未实现
  - 状态：仅配置占位，无 `notion_integration.py`、无 `notion_config.json`、无 HTTP 调用

**网络 HTTP 客户端:**
- 主应用模块（`main.py`、`categorizer.py`、`data_loader.py`、`learning_engine.py`、`gui_interface.py`、`data_exporter.py`）无 `requests`、`urllib`、`aiohttp` 等网络依赖
- 应用为完全离线桌面工具

## Data Storage

**Databases:**
- 无关系型或 NoSQL 数据库
- 持久化全部基于本地 JSON 文件：
  - `bill_rules_optimized.json` — 分类规则（`learning_engine.py` → `save_data` / `_load_data`）
  - `bill_history.json` — 分类历史（同上）
  - `config.json` — 应用配置（`config.py` → `ConfigManager`）
- 遗留脚本 `WeChatBillCategorizer.py` 另用 `pickle` + `gzip` 压缩规则文件（与模块化代码路径并行，非主入口）

**File Storage:**
- 本地文件系统 exclusively
- 典型目录（仓库内或用户工作目录）：
  - `原始账单/` — 未分类导入文件
  - `已分类/` — 已导出 CSV（按年分子目录，如 `已分类/2026/`）
  - `分类明细/` — `bill_analyzer.py` 生成的分类汇总 CSV
- 导出格式：UTF-8-SIG CSV（`data_exporter.py` → `export_to_csv`）
- `bill_analyzer.py` 另输出 PNG 图表（`matplotlib` `savefig`）

**Caching:**
- 无外部缓存服务
- 内存内索引：`learning_engine.py` 中 `merchant_index`（`defaultdict`）加速规则查询

## Authentication & Identity

**Auth Provider:**
- 无用户认证或身份提供商
- 应用级“人员”字段为配置枚举（`config.json` → `categories.people_options`：如「男主人」「女主人」「袁程波」「杜雨秦」），用于账单标注，非登录身份

## Monitoring & Observability

**Error Tracking:**
- 无 Sentry、Datadog 等外部错误追踪

**Logs:**
- `print()` 标准输出（含 emoji 状态提示）
- 异常时 `traceback.print_exc()`（`main.py`、`data_loader.py`、`test_gui.py`）
- GUI 错误通过 `tkinter.messagebox` 展示（`main.py`、`gui_interface.py`）
- `.cursor/debug.log` 存在但非应用内置日志框架

## CI/CD & Deployment

**Hosting:**
- 无云托管；产物为 PyInstaller 本地可执行目录 `dist/BillCategorizer/`

**CI Pipeline:**
- GitHub Actions — `.github/workflows/python-package-conda.yml`
  - 触发：`on: [push]`
  - Jobs：`build-linux`（ubuntu-latest）、`build-windows`（windows-latest）
  - 步骤：checkout → Python 3.10 → 安装依赖 → flake8 → pytest（GUI 测试在 CI 中 skip）→ PyInstaller 构建 → upload-artifact
  - Linux 额外：Conda `environment.yml` 更新、Xvfb 虚拟显示
  - Windows：`pip install pandas openpyxl pytest flake8 pyinstaller`
  - Artifacts：`BillCategorizer-linux`、`BillCategorizer-windows`（`dist/BillCategorizer/`，保留 30 天）

## Environment Configuration

**Required env vars:**
- 业务逻辑无必需环境变量
- CI 测试使用：
  - `CI=true`
  - `GITHUB_ACTIONS=true`（`test_gui.py` 据此跳过 GUI 测试）
- Linux CI GUI 测试：`DISPLAY=:99`（配合 Xvfb）

**Secrets location:**
- 无 `.env` 或密钥文件（forbidden/未检出）
- 无 API key、OAuth token 或云服务凭证集成

## Webhooks & Callbacks

**Incoming:**
- 无 HTTP 服务端、无 webhook 端点

**Outgoing:**
- 无对外 webhook 或回调 URL 调用

## Third-Party Tooling (Non-Runtime)

**Version Control / CI:**
- Git + GitHub（`.github/workflows/`）
- `gh` CLI 可用于 PR/Issue（非应用运行时依赖）

**Editor:**
- VS Code / Cursor（`.vscode/settings.json` — Black 格式化）

## Integration Summary for Implementers

| 集成类型 | 状态 | 关键文件 |
|---------|------|---------|
| 微信/支付宝账单文件 | 已实现（离线） | `data_loader.py` |
| CSV/Excel 导出 | 已实现 | `data_exporter.py` |
| JSON 规则持久化 | 已实现 | `learning_engine.py`, `bill_rules_optimized.json` |
| Notion 同步 | 未实现（仅配置占位） | `config.py`, `README.md` |
| 云数据库 / API | 未使用 | — |
| 用户认证 | 不适用 | — |

新增外部集成时：在仓库根目录新增独立模块（参考 README 中 `notion_integration.py` 规划），通过 `ConfigManager.get_file_path()` 或 `config.json` 扩展配置，避免在 `data_loader.py` / `categorizer.py` 中直接耦合 HTTP 客户端。

---

*Integration audit: 2026-06-08*
