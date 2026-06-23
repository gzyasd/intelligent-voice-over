# IVO 便携版打包脚本
# 用途：将 .venv 和 .venv-pyannote 复制到安装目录的 resources/ 下
# 使用方法：安装 IVO Setup 后，运行此脚本，选择 IVO 安装目录

param(
    [Parameter(Mandatory=$true, HelpMessage="IVO 安装目录路径（如 D:\IVO 或 C:\Program Files\IVO）")]
    [string]$InstallDir
)

$ErrorActionPreference = "Stop"

# 验证安装目录
$resourcesDir = Join-Path $InstallDir "resources"
if (-not (Test-Path $resourcesDir)) {
    Write-Error "未找到 resources 目录: $resourcesDir`n请确认 IVO 安装路径是否正确。"
    exit 1
}

# 获取脚本所在目录（项目根目录）
$projectRoot = $PSScriptRoot
if (-not (Test-Path (Join-Path $projectRoot ".venv"))) {
    Write-Error "未找到 .venv 目录: $projectRoot\.venv`n请确认脚本位于项目根目录。"
    exit 1
}

# 复制 .venv
$venvSrc = Join-Path $projectRoot ".venv"
$venvDst = Join-Path $resourcesDir ".venv"
if (Test-Path $venvDst) {
    Write-Host ".venv 已存在于目标目录，跳过复制。" -ForegroundColor Yellow
} else {
    Write-Host "正在复制 .venv 到 $venvDst ..." -ForegroundColor Cyan
    Write-Host "（约 6GB，可能需要几分钟）"
    Copy-Item $venvSrc $venvDst -Recurse -Force
    Write-Host ".venv 复制完成。" -ForegroundColor Green
}

# 复制 .venv-pyannote
$pyannoteSrc = Join-Path $projectRoot ".venv-pyannote"
$pyannoteDst = Join-Path $resourcesDir ".venv-pyannote"
if (Test-Path $pyannoteSrc) {
    if (Test-Path $pyannoteDst) {
        Write-Host ".venv-pyannote 已存在于目标目录，跳过复制。" -ForegroundColor Yellow
    } else {
        Write-Host "正在复制 .venv-pyannote 到 $pyannoteDst ..." -ForegroundColor Cyan
        Write-Host "（约 4.5GB，可能需要几分钟）"
        Copy-Item $pyannoteSrc $pyannoteDst -Recurse -Force
        Write-Host ".venv-pyannote 复制完成。" -ForegroundColor Green
    }
} else {
    Write-Host ".venv-pyannote 不存在，跳过。" -ForegroundColor Yellow
}

# 确保 pip 可用（uv sync 创建的 venv 默认无 pip）
Write-Host ""
Write-Host "=== 检查并引导 pip ===" -ForegroundColor Cyan
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$venvPython = Join-Path $venvDst "Scripts\python.exe"
$pyannotePython = Join-Path $pyannoteDst "Scripts\python.exe"

foreach ($py in @($venvPython, $pyannotePython)) {
    if (-not (Test-Path $py)) {
        continue
    }
    $venvName = if ($py -like "*pyannote*") { ".venv-pyannote" } else { ".venv" }
    # 检查 pip 是否可用
    & $py -m pip --version 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] $venvName 已有 pip" -ForegroundColor Green
    } else {
        Write-Host "[INFO] $venvName 缺少 pip，正在通过 ensurepip 引导..." -ForegroundColor Yellow
        & $py -m ensurepip --upgrade 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] $venvName pip 引导成功" -ForegroundColor Green
        } else {
            Write-Host "[WARN] $venvName ensurepip 失败，程序启动后安装依赖时会自动重试" -ForegroundColor Yellow
        }
    }
}

# 验证
Write-Host ""
Write-Host "=== 验证 ===" -ForegroundColor Cyan
if (Test-Path $venvPython) {
    Write-Host "[OK] .venv\Scripts\python.exe 存在" -ForegroundColor Green
} else {
    Write-Host "[FAIL] .venv\Scripts\python.exe 不存在" -ForegroundColor Red
}
if (Test-Path $pyannotePython) {
    Write-Host "[OK] .venv-pyannote\Scripts\python.exe 存在" -ForegroundColor Green
} else {
    Write-Host "[FAIL] .venv-pyannote\Scripts\python.exe 不存在" -ForegroundColor Red
}

Write-Host ""
Write-Host "完成！现在可以运行 IVO.exe 了。" -ForegroundColor Green
