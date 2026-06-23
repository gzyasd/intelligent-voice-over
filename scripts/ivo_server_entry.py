"""PyInstaller entry point for the IVO Python backend.

This wrapper lives outside the ``server`` package so that PyInstaller can run
it as ``__main__`` without breaking the relative imports inside
``server/main.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
src_dir = project_root / "src"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from server.main import main  # noqa: E402

if __name__ == "__main__":
    main()
