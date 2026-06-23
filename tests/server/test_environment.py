"""环境诊断 API 测试"""

from __future__ import annotations


async def test_diagnostics(client):
    response = await client.get("/environment/diagnostics")
    assert response.status_code == 200
    data = response.json()
    assert "python_version" in data


async def test_optional_dependencies(client):
    response = await client.get("/environment/optional-dependencies")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
