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
# The delegated builder uses the Electron workflow:
# frontend build -> PyInstaller backend -> electron-builder installer.

Write-Host "Running tests and quality checks before packaging..."
uv sync
uv run pytest
uv run ruff check .
uv run mypy src server

pnpm install --frozen-lockfile
pnpm run typecheck

Write-Host "Building Windows desktop package..."
pnpm run build:win

Write-Host "Package output: .\dist-installer"
Write-Host "Review installer contents before publishing. Do not include models, media, or secrets."
