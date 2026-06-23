"""pytest 配置：确保 server 和 ivo 在 sys.path 中"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = str(_ROOT / "src")
_SERVER = str(_ROOT / "server")
for p in (_SRC, _SERVER):
    if p not in sys.path:
        sys.path.insert(0, p)
