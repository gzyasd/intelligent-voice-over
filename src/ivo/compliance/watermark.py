from __future__ import annotations

import platform
from pathlib import Path

from pydantic import BaseModel


class WatermarkOptions(BaseModel):
    enabled: bool
    text: str


def build_watermark_filter(options: WatermarkOptions) -> str | None:
    if not options.enabled:
        return None
    escaped_text = options.text.replace("\\", "\\\\").replace("'", "\\'")
    fontfile = _default_fontfile_filter_option()
    return (
        "drawtext="
        f"{fontfile}"
        f"text='{escaped_text}':"
        "x=w-tw-24:y=24:"
        "fontsize=24:"
        "fontcolor=white:"
        "box=1:"
        "boxcolor=black@0.45"
    )


def _default_fontfile_filter_option() -> str:
    if platform.system() != "Windows":
        return ""

    font_path = Path("C:/Windows/Fonts/arial.ttf")
    if not font_path.is_file():
        return ""

    escaped_path = str(font_path).replace("\\", "/").replace(":", "\\:")
    return f"fontfile='{escaped_path}':"
