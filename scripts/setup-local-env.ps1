<#
.SYNOPSIS
    One-shot environment setup for Intelligent Voice Over local model runtimes.
.DESCRIPTION
    Installs ALL Python dependencies needed by every local model service:

        1. uv sync --dev --all-extras  →  main venv (core + dev + all optional deps)
        2. Create .venv-pyannote        →  isolated venv for pyannote.audio
        3. Verify every module is importable

    Run this once after cloning the repository.
    Model weights are NOT downloaded — run setup-local-models.ps1 separately.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot

Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Intelligent Voice Over — Local Environment Setup  ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot`n" -ForegroundColor Gray

# ── Helper ──────────────────────────────────────────────────────────────────
$AllPassed = $true
$Results = @()

function Step-Start {
    param([string]$Label)
    Write-Host "» $Label ... " -NoNewline
}

function Step-Ok {
    Write-Host "✔" -ForegroundColor Green
    $script:Results += "  ✔  $($script:CurrentStep)"
}

function Step-Fail {
    param([string]$Detail)
    Write-Host "✘" -ForegroundColor Red
    if ($Detail) { Write-Host "     $Detail" -ForegroundColor Red }
    $script:AllPassed = $false
    $script:Results += "  ✘  $($script:CurrentStep)"
}

# ── 1. uv check & sync ─────────────────────────────────────────────────────
Write-Host "── Step 1: uv 包管理器 ────────────────────────────────" -ForegroundColor Yellow
$script:CurrentStep = "检查 uv 可用"
Step-Start "检查 uv 可用"
$uvPath = Get-Command "uv" -ErrorAction SilentlyContinue
if (-not $uvPath) {
    Step-Fail "uv 未找到。安装: https://docs.astral.sh/uv/getting-started/installation/"
    # Cannot continue without uv
    Pop-Location
    exit 1
}
Step-Ok

$script:CurrentStep = "uv sync --dev --all-extras（主环境 + 所有模型依赖）"
Step-Start $script:CurrentStep
$syncOutput = uv sync --dev --all-extras 2>&1
if ($LASTEXITCODE -ne 0) {
    Step-Fail "uv sync 失败"
    Write-Host "    $syncOutput" -ForegroundColor Red
} else {
    Step-Ok
}

# ── 2. pyannote.audio 独立虚拟环境 ──────────────────────────────────────
Write-Host "`n── Step 2: pyannote.audio 独立环境 (.venv-pyannote) ───" -ForegroundColor Yellow

$PyannoteVenv = Join-Path $ProjectRoot ".venv-pyannote"
$PyannotePython = Join-Path $PyannoteVenv "Scripts" "python.exe"

if (Test-Path $PyannotePython) {
    $script:CurrentStep = "检测到 .venv-pyannote 已存在，验证 pyannote.audio"
    Step-Start $script:CurrentStep
    $check = & $PyannotePython -c "from importlib import import_module; import_module('pyannote.audio'); print('ok')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Step-Ok
    } else {
        Step-Fail "pyannote.audio 不可导入，将重新安装"
        $script:CurrentStep = "重新安装 pyannote.audio 到 .venv-pyannote"
        Step-Start $script:CurrentStep
        $installOut = uv venv --python 3.10 ".venv-pyannote" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $installOut = & $PyannoteVenv\Scripts\python.exe -m pip install pyannote.audio 2>&1
            if ($LASTEXITCODE -eq 0) { Step-Ok } else { Step-Fail "pip install 失败"; Write-Host "    $installOut" }
        } else {
            Step-Fail "uv venv 创建失败"
        }
    }
} else {
    $script:CurrentStep = "创建 .venv-pyannote 并安装 pyannote.audio（较长时间下载）"
    Step-Start $script:CurrentStep
    $installOut = uv venv --python 3.10 ".venv-pyannote" 2>&1
    if ($LASTEXITCODE -eq 0) {
        $installOut = & $PyannoteVenv\Scripts\python.exe -m pip install pyannote.audio 2>&1
        if ($LASTEXITCODE -eq 0) { Step-Ok } else { Step-Fail "pip install 失败"; Write-Host "    $installOut" }
    } else {
        Step-Fail "uv venv 创建失败"
    }
}

# ── 3. 验证全部模块可导入 ─────────────────────────────────────────────
Write-Host "`n── Step 3: 验证所有模块可导入 ─────────────────────────" -ForegroundColor Yellow

$MainVenvPython = Join-Path $ProjectRoot ".venv" "Scripts" "python.exe"

$VerifyCases = @(
    @{ Import = "demucs";       ExpectedVenv = "main";     Label = "Demucs（人声分离）" }
    @{ Import = "faster_whisper"; ExpectedVenv = "main";   Label = "faster-whisper（ASR）" }
    @{ Import = "transformers";   ExpectedVenv = "main";   Label = "transformers（Whisper turbo）" }
    @{ Import = "f5_tts";       ExpectedVenv = "main";     Label = "F5-TTS（语音合成）" }
    @{ Import = "cosyvoice";    ExpectedVenv = "main";     Label = "CosyVoice（语音合成）" }
    @{ Import = "pyannote.audio"; ExpectedVenv = "pyannote"; Label = "pyannote.audio（说话人识别）" }
)

foreach ($case in $VerifyCases) {
    $script:CurrentStep = $case.Label
    Step-Start $script:CurrentStep

    $pythonExe = if ($case.ExpectedVenv -eq "pyannote") { $PyannotePython } else { $MainVenvPython }
    $code = "from importlib import import_module; import_module('$($case.Import)')"

    if (-not (Test-Path $pythonExe)) {
        Step-Fail "Python 解释器未找到: $pythonExe"
        continue
    }

    $result = & $pythonExe -c $code 2>&1
    if ($LASTEXITCODE -eq 0) {
        Step-Ok
    } else {
        $err = ($result | Out-String).Trim()
        Step-Fail $err
    }
}

# ── Summary ──────────────────────────────────────────────────────────────
Write-Host "`n═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
if ($AllPassed) {
    Write-Host "  全部环境就绪！模型依赖已安装完成。" -ForegroundColor Green
    Write-Host "  模型权重需另行下载，请运行:" -ForegroundColor Gray
    Write-Host "    scripts\setup-local-models.ps1" -ForegroundColor Gray
} else {
    Write-Host "  部分步骤未通过，请检查上方 ✘ 标记的项目。" -ForegroundColor Yellow
    Write-Host "  排查后重新运行此脚本即可。" -ForegroundColor Yellow
}
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan

Pop-Location
if (-not $AllPassed) { exit 1 }