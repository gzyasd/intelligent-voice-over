"""server 测试的 pytest fixtures"""

from __future__ import annotations

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中，使 server 包可导入
_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from server.main import app  # noqa: E402


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
