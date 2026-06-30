<#
.SYNOPSIS
    Build self-contained portable Python venvs from existing .venv and .venv-pyannote.
.DESCRIPTION
    Uses Python embeddable package as the base Python runtime, then copies
    site-packages from the existing .venv and .venv-pyannote directories.
    No need to re-download torch, demucs, f5-tts, pyannote.audio etc.

    Outputs two zip files:
    - ivo-venv-portable.zip          (main venv: torch/demucs/f5-tts etc.)
    - ivo-venv-pyannote-portable.zip (pyannote.audio venv)
.PARAMETER OutputDir
    Output directory, default: dist-portable-venv
.PARAMETER PythonVersion
    Python embeddable version, default: 3.10.11
.PARAMETER SourceVenv
    Path to existing .venv, default: .venv (relative to project root)
.PARAMETER SourcePyannoteVenv
    Path to existing .venv-pyannote, default: .venv-pyannote (relative to project root)
.EXAMPLE
    .\scripts\build-portable-venv.ps1
#>

param(
    [string]$OutputDir = "dist-portable-venv",
    [string]$PythonVersion = "3.10.11",
    [string]$SourceVenv = "D:\临时软件包\IVO-Resource\venv\.venv",
    [string]$SourcePyannoteVenv = "D:\临时软件包\IVO-Resource\venv\.venv-pyannote"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot

# Resolve source paths: absolute paths are used as-is, relative paths are joined with project root
function Resolve-SourcePath {
    param([string]$P)
    if ([System.IO.Path]::IsPathRooted($P)) { return $P } else { return Join-Path $ProjectRoot $P }
}
$SourceVenvFull = Resolve-SourcePath $SourceVenv
$SourcePyannoteVenvFull = Resolve-SourcePath $SourcePyannoteVenv

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  IVO Portable Venv Builder" -ForegroundColor Cyan
Write-Host "  (copy mode: reuse existing site-packages)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Python embeddable: $PythonVersion"
Write-Host "Source .venv: $SourceVenvFull"
Write-Host "Source .venv-pyannote: $SourcePyannoteVenvFull"
Write-Host "Output: $OutputDir"
Write-Host ""

# ── Validate source venvs ─────────────────────────────────────────────────
$SrcMainSitePackages = Join-Path $SourceVenvFull "Lib\site-packages"
$SrcPyannoteSitePackages = Join-Path $SourcePyannoteVenvFull "Lib\site-packages"

if (-not (Test-Path $SrcMainSitePackages)) {
    Write-Error "Source venv site-packages not found: $SrcMainSitePackages`nRun 'uv sync --dev' first to create .venv"
    exit 1
}
if (-not (Test-Path $SrcPyannoteSitePackages)) {
    Write-Error "Source pyannote venv site-packages not found: $SrcPyannoteSitePackages`nRun '.\scripts\setup-local-env.ps1' first to create .venv-pyannote"
    exit 1
}

Write-Host "[OK] Source venvs found" -ForegroundColor Green
$MainPkgCount = (Get-ChildItem $SrcMainSitePackages -Directory).Count
$PyannotePkgCount = (Get-ChildItem $SrcPyannoteSitePackages -Directory).Count
Write-Host "  .venv packages: $MainPkgCount dirs"
Write-Host "  .venv-pyannote packages: $PyannotePkgCount dirs"
Write-Host ""

# ── Prepare work dir ──────────────────────────────────────────────────────
$WorkDir = Join-Path $ProjectRoot "build-portable-tmp"
$OutputFullPath = Join-Path $ProjectRoot $OutputDir
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
New-Item -ItemType Directory -Force -Path $OutputFullPath | Out-Null

# ── Download Python embeddable ────────────────────────────────────────────
$PythonZip = Join-Path $WorkDir "python-embed.zip"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"

if (-not (Test-Path $PythonZip)) {
    Write-Host "[1/7] Downloading Python $PythonVersion embeddable..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $PythonUrl -OutFile $PythonZip -UseBasicParsing
    Write-Host "  Done" -ForegroundColor Green
} else {
    Write-Host "[1/7] Python embeddable already exists, skip" -ForegroundColor Gray
}

# ── Helper: create embeddable Python env ──────────────────────────────────
function New-EmbeddableEnv {
    param([string]$TargetDir)

    if (Test-Path $TargetDir) { Remove-Item $TargetDir -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

    # Extract Python embeddable
    Expand-Archive -Path $PythonZip -DestinationPath $TargetDir -Force

    # Enable site-packages (uncomment "import site" in _pth file)
    $pthFile = Get-ChildItem -Path $TargetDir -Filter "python*._pth" | Select-Object -First 1
    if ($pthFile) {
        $content = Get-Content $pthFile.FullName
        $content = $content | ForEach-Object { if ($_ -eq "#import site") { "import site" } else { $_ } }
        # Add Lib\site-packages path
        $content += "Lib\site-packages"
        Set-Content -Path $pthFile.FullName -Value $content
    }

    # Create Lib\site-packages directory
    $spDir = Join-Path $TargetDir "Lib\site-packages"
    New-Item -ItemType Directory -Force -Path $spDir | Out-Null
}

# ── Build main .venv ──────────────────────────────────────────────────────
Write-Host "[2/7] Building main portable venv..." -ForegroundColor Yellow
$MainVenvDir = Join-Path $WorkDir ".venv"
New-EmbeddableEnv -TargetDir $MainVenvDir

Write-Host "  Copying site-packages from existing .venv..." -ForegroundColor Gray
$DestMainSP = Join-Path $MainVenvDir "Lib\site-packages"
Copy-Item -Path "$SrcMainSitePackages\*" -Destination $DestMainSP -Recurse -Force
Write-Host "  Done" -ForegroundColor Green

# ── Build .venv-pyannote ──────────────────────────────────────────────────
Write-Host "[3/7] Building pyannote portable venv..." -ForegroundColor Yellow
$PyannoteVenvDir = Join-Path $WorkDir ".venv-pyannote"
New-EmbeddableEnv -TargetDir $PyannoteVenvDir

Write-Host "  Copying site-packages from existing .venv-pyannote..." -ForegroundColor Gray
$DestPyannoteSP = Join-Path $PyannoteVenvDir "Lib\site-packages"
Copy-Item -Path "$SrcPyannoteSitePackages\*" -Destination $DestPyannoteSP -Recurse -Force
Write-Host "  Done" -ForegroundColor Green

# ── Verify ────────────────────────────────────────────────────────────────
$MainPython = Join-Path $MainVenvDir "python.exe"
$PyannotePython = Join-Path $PyannoteVenvDir "python.exe"

Write-Host "[4/7] Verifying main venv modules..." -ForegroundColor Yellow
$VerifyModules = @("demucs", "faster_whisper", "f5_tts", "torch", "transformers")
foreach ($mod in $VerifyModules) {
    $ErrorActionPreference = "Continue"
    $result = & $MainPython -c "import $mod; print('ok')" 2>&1
    $ErrorActionPreference = "Stop"
    if ($result -eq "ok") {
        Write-Host "  [OK] $mod" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $mod" -ForegroundColor Red
    }
}

Write-Host "[5/7] Verifying pyannote venv..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
$pyannoteResult = & $PyannotePython -c "import pyannote.audio; print('ok')" 2>&1
$ErrorActionPreference = "Stop"
if ($pyannoteResult -eq "ok") {
    Write-Host "  [OK] pyannote.audio" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] pyannote.audio" -ForegroundColor Red
}

# ── Pack zip ──────────────────────────────────────────────────────────────
Write-Host "[6/7] Packing zip..." -ForegroundColor Yellow

$MainZip = Join-Path $OutputFullPath "ivo-venv-portable.zip"
$PyannoteZip = Join-Path $OutputFullPath "ivo-venv-pyannote-portable.zip"

if (Test-Path $MainZip) { Remove-Item $MainZip -Force }
if (Test-Path $PyannoteZip) { Remove-Item $PyannoteZip -Force }

Write-Host "  Compressing .venv (large, may take a few minutes)..." -ForegroundColor Gray
Compress-Archive -Path "$MainVenvDir\*" -DestinationPath $MainZip -CompressionLevel Optimal
Write-Host "  ivo-venv-portable.zip done" -ForegroundColor Green

Write-Host "  Compressing .venv-pyannote..." -ForegroundColor Gray
Compress-Archive -Path "$PyannoteVenvDir\*" -DestinationPath $PyannoteZip -CompressionLevel Optimal
Write-Host "  ivo-venv-pyannote-portable.zip done" -ForegroundColor Green

# ── Cleanup and output ────────────────────────────────────────────────────
Write-Host "[7/7] Cleaning up temp files..." -ForegroundColor Yellow
Remove-Item $WorkDir -Recurse -Force

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Build complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Output files:" -ForegroundColor White
$MainSize = [math]::Round((Get-Item $MainZip).Length / 1GB, 2)
$PyannoteSize = [math]::Round((Get-Item $PyannoteZip).Length / 1GB, 2)
Write-Host "  $MainZip ($MainSize GB)"
Write-Host "  $PyannoteZip ($PyannoteSize GB)"
Write-Host ""
Write-Host "Usage:" -ForegroundColor White
Write-Host "  1. Download ivo-venv-portable.zip, extract to install dir resources\.venv\"
Write-Host "  2. Download ivo-venv-pyannote-portable.zip, extract to install dir resources\.venv-pyannote\"
Write-Host ""

Pop-Location
