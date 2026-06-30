<#
.SYNOPSIS
    Split large files into <2GB parts for GitHub Release upload, and generate merge.bat.
.DESCRIPTION
    GitHub Release assets are limited to 2 GB each. This script splits large zip files
    into 1.9 GB parts (file.zip.001.part, file.zip.002.part, ...) and generates a
    merge.bat that users can double-click to reassemble the original zip via copy /b.
.PARAMETER Files
    Array of file paths to split.
.PARAMETER PartSizeMB
    Part size in MB, default 1900 (< 2 GB GitHub limit).
.EXAMPLE
    .\scripts\split-and-merge.ps1 -Files "dist-portable-venv\ivo-venv-portable.zip","dist-portable-venv\ivo-venv-pyannote-portable.zip"
#>

param(
    [Parameter(Mandatory=$true)]
    [string[]]$Files,
    [int]$PartSizeMB = 1900
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot

$PartSize = [int64]$PartSizeMB * 1MB
$Buffer = New-Object byte[] 1048576  # 1 MB buffer

function Split-File {
    param([string]$Path, [int64]$Size)
    $total = (Get-Item $Path).Length
    $parts = [math]::Ceiling([double]$total / $Size)
    Write-Host "Splitting $Path ($([math]::Round($total/1GB,2)) GB) into $parts parts..." -ForegroundColor Yellow

    $inStream = [System.IO.File]::OpenRead($Path)
    try {
        $partNum = 1
        $bytesWritten = [int64]0
        while ($bytesWritten -lt $total) {
            $outPath = "$Path.$($partNum.ToString('00')).part"
            $outStream = [System.IO.File]::Create($outPath)
            $partBytes = [int64]0
            try {
                while ($partBytes -lt $Size -and $bytesWritten -lt $total) {
                    $toRead = [math]::Min([math]::Min([int64]$Buffer.Length, $Size - $partBytes), $total - $bytesWritten)
                    $read = $inStream.Read($Buffer, 0, [int]$toRead)
                    if ($read -le 0) { break }
                    $outStream.Write($Buffer, 0, $read)
                    $partBytes += $read
                    $bytesWritten += $read
                }
            } finally { $outStream.Close() }
            Write-Host ("  {0} ({1} MB)" -f $outPath, [math]::Round($partBytes/1MB,1)) -ForegroundColor Gray
            $partNum++
        }
    } finally { $inStream.Close() }

    # Generate merge.bat for this file
    $baseName = Split-Path $Path -Leaf
    $batName = "merge-$($baseName -replace '\.zip$','').bat"
    $batPath = Join-Path (Split-Path $Path) $batName
    $mergeCmd = "@echo off`r`necho Merging $baseName ...`r`ncopy /b `"$baseName.0*.part`" `"$baseName`" >nul`r`nif errorlevel 1 (`r`n  echo Merge FAILED`r`n  pause`r`n  exit /b 1`r`n) else (`r`n  echo Merge OK: $baseName`r`n  echo You can now delete the .part files and extract $baseName`r`n  pause`r`n)"
    Set-Content -Path $batPath -Value $mergeCmd -Encoding ASCII
    Write-Host "  Generated $batName" -ForegroundColor Green
    Write-Host ""
}

foreach ($f in $Files) {
    if (-not (Test-Path $f)) {
        Write-Error "File not found: $f"
        exit 1
    }
    Split-File -Path $f -Size $PartSize
}

Write-Host "Done. Upload all .part files and merge-*.bat to GitHub Release." -ForegroundColor Cyan
Pop-Location
