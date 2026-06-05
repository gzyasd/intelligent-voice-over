$ErrorActionPreference = "Stop"

# Windows packaging wrapper for Intelligent Voice Over.
# Excluded from release/package review:
# - models/
# - 测试视频/
# - sample_media/
# - scratch/
# - *.mp4
# - *.wav
# - .env
# - API keys, HF_TOKEN, ModelScope token, and other secrets.
#
# The delegated builder invokes PyInstaller through:
# uv tool run pyinstaller --name IntelligentVoiceOver --windowed ...

Write-Host "Running tests and quality checks before packaging..."
uv sync
uv run pytest
uv run ruff check .
uv run mypy src

Write-Host "Building Windows desktop package..."
uv run python .\scripts\build_windows_package.py --output-dir .\dist

Write-Host "Package output: .\dist\IntelligentVoiceOver"
Write-Host "Review release-manifest.json before publishing. Do not include models, media, or secrets."
