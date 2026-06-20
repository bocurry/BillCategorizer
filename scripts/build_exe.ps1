# 打包 BillCategorizer 为 Windows 可执行目录
# 用法（在项目根目录）:
#   pip install pyinstaller
#   powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> pytest"
python -m pytest test_gui.py test_phase1_integration.py test_app_paths.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> PyInstaller"
python -m PyInstaller --noconfirm build.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Exe = Join-Path $Root "dist\BillCategorizer\BillCategorizer.exe"
if (-not (Test-Path $Exe)) {
    Write-Error "未找到 $Exe"
}
Write-Host "==> OK: $Exe"
Write-Host "将账单 xlsx/csv 放在 dist\BillCategorizer\ 目录下，双击 BillCategorizer.exe 运行。"
