from __future__ import annotations

from pathlib import Path


def workspace_root(root: Path | None = None) -> Path:
    return (root or Path.cwd()).resolve()


def default_runs_dir(*, root: Path | None = None) -> Path:
    return workspace_root(root) / "runs"


def default_work_dir(*, root: Path | None = None) -> Path:
    return workspace_root(root) / ".ivo-work"


def default_user_settings_path(*, root: Path | None = None) -> Path:
    return default_work_dir(root=root) / "user-settings.json"
