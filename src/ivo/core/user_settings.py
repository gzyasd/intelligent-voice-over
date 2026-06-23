from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

ThemeMode = Literal["light", "dark", "system"]
PipMirrorKey = Literal["official", "tsinghua", "aliyun", "ustc"]

# PyPI mirrors: (label, pip index URL)
# pip install -i {url}; empty string = official PyPI (no -i flag)
PYPI_MIRRORS: dict[PipMirrorKey, tuple[str, str]] = {
    "official": ("官方 PyPI", ""),
    "tsinghua": ("清华大学 TUNA", "https://pypi.tuna.tsinghua.edu.cn/simple"),
    "aliyun": ("阿里云", "https://mirrors.aliyun.com/pypi/simple"),
    "ustc": ("中科大 USTC", "https://pypi.mirrors.ustc.edu.cn/simple"),
}


class UserSettings(BaseModel):
    models_dir: Path
    projects_dir: Path
    preferred_preset_id: str = "local_quality_lmstudio_qwen_f5"
    prefer_gpu: bool = True
    lm_studio_base_url: str = "http://127.0.0.1:1995/v1"
    recent_projects: list[Path] = Field(default_factory=list)
    theme: ThemeMode = "light"
    pip_mirror: PipMirrorKey = "official"
    # 自定义 venv Python 解释器路径（绝对路径）。为 None 时使用默认搜索逻辑。
    custom_venv_python: Path | None = None
    custom_pyannote_python: Path | None = None

    @classmethod
    def with_defaults(cls, *, runtime_root: Path) -> UserSettings:
        root = runtime_root.resolve()
        return cls(
            models_dir=root / "models",
            projects_dir=root / "runs",
        )


class UserSettingsStore:
    def __init__(self, path: Path, *, runtime_root: Path) -> None:
        self.path = path
        self.runtime_root = runtime_root

    def load(self) -> UserSettings:
        if not self.path.is_file():
            return UserSettings.with_defaults(runtime_root=self.runtime_root)
        stored = UserSettings.model_validate(json.loads(self.path.read_text(encoding="utf-8")))
        defaults = UserSettings.with_defaults(runtime_root=self.runtime_root)
        return defaults.model_copy(update=stored.model_dump())

    def save(self, settings: UserSettings) -> UserSettings:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
        return settings

    def add_recent_project(self, project_path: Path) -> UserSettings:
        settings = self.load()
        resolved = project_path.resolve()
        recent = [path for path in settings.recent_projects if path.resolve() != resolved]
        recent.insert(0, resolved)
        return self.save(settings.model_copy(update={"recent_projects": recent[:20]}))

    def remove_recent_project(self, project_path: Path) -> UserSettings:
        settings = self.load()
        resolved = project_path.resolve()
        recent = [path for path in settings.recent_projects if path.resolve() != resolved]
        return self.save(settings.model_copy(update={"recent_projects": recent}))
