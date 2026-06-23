"""项目 CRUD API 测试"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def patch_settings(tmp_path: Path, monkeypatch):
    """用临时目录替换用户设置"""
    from server import dependencies
    from ivo.core.user_settings import UserSettingsStore

    projects_dir = tmp_path / "runs"
    projects_dir.mkdir()
    store = UserSettingsStore(tmp_path / "settings.json", runtime_root=tmp_path)
    monkeypatch.setattr(dependencies, "get_user_settings_store", lambda: store)
    return store


async def test_list_projects_empty(client, patch_settings):
    """空项目库"""
    response = await client.get("/projects")
    assert response.status_code == 200
    assert response.json() == []


async def test_create_and_get_project(client, patch_settings, tmp_path: Path):
    """创建项目并获取详情"""
    # 准备源素材
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"fake video")

    # 创建项目
    response = await client.post("/projects", json={
        "source_media_path": str(source_video),
        "name": "TestProject",
        "source_language": "en",
        "target_language": "zh",
        "content_type": "video",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TestProject"
    assert data["source_language"] == "en"

    # 获取项目详情
    project_path = patch_settings.load().projects_dir / "TestProject.ivoproj"
    response = await client.get("/projects/detail", params={"path": str(project_path)})
    assert response.status_code == 200
    assert response.json()["name"] == "TestProject"

    # 获取项目状态
    response = await client.get("/projects/status", params={"path": str(project_path)})
    assert response.status_code == 200
    assert response.json()["lifecycle"] == "not_started"


async def test_project_status_uses_active_pipeline_runner(
    client,
    patch_settings,
    tmp_path: Path,
    monkeypatch,
) -> None:
    from server import pipeline_runner
    from ivo.core.project import DubbingProject

    project_path = patch_settings.load().projects_dir / "RunningProject.ivoproj"
    project = DubbingProject.create(
        project_path,
        name="RunningProject",
        source_language="ja",
        target_language="zh",
    )
    project.mark_generation_started(now=100.0)
    project.jobs.mark_running("tts")
    monkeypatch.setattr(
        pipeline_runner,
        "get_active_project_paths",
        lambda: {project.path.resolve()},
    )

    response = await client.get("/projects/status", params={"path": str(project.path)})

    assert response.status_code == 200
    assert response.json()["lifecycle"] == "running"
    assert response.json()["status_label"] == "生成中"
    assert response.json()["primary_action"] == "progress"


async def test_create_project_with_scheme_persists_selection(
    client, patch_settings, tmp_path: Path, monkeypatch
):
    """Creating a project should persist the selected dubbing scheme."""
    from server import dependencies
    from ivo.model_services.provider_config import DubbingScheme
    from ivo.model_services.provider_store import ProviderStore

    provider_store = ProviderStore(tmp_path / "provider-store")
    provider_store.save_scheme(
        DubbingScheme(id="scheme-local", display_name="Local Scheme", bindings=[])
    )
    monkeypatch.setattr(dependencies, "get_provider_store", lambda: provider_store)

    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"fake video")

    response = await client.post(
        "/projects",
        json={
            "source_media_path": str(source_video),
            "name": "SchemeProject",
            "source_language": "en",
            "target_language": "zh",
            "content_type": "video",
            "scheme_id": "scheme-local",
        },
    )

    assert response.status_code == 200
    assert response.json()["scheme_id"] == "scheme-local"

    project_path = patch_settings.load().projects_dir / "SchemeProject.ivoproj"
    response = await client.get("/projects/detail", params={"path": str(project_path)})
    assert response.status_code == 200
    assert response.json()["scheme_id"] == "scheme-local"


async def test_create_project_rejects_missing_scheme(
    client, patch_settings, tmp_path: Path, monkeypatch
):
    """The API should not accept a project scheme id that no longer exists."""
    from server import dependencies
    from ivo.model_services.provider_store import ProviderStore

    provider_store = ProviderStore(tmp_path / "provider-store")
    monkeypatch.setattr(dependencies, "get_provider_store", lambda: provider_store)

    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"fake video")

    response = await client.post(
        "/projects",
        json={
            "source_media_path": str(source_video),
            "name": "BadSchemeProject",
            "source_language": "en",
            "scheme_id": "missing-scheme",
        },
    )

    assert response.status_code == 404


async def test_delete_project(client, patch_settings, tmp_path: Path):
    """删除项目"""
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"fake")

    # 创建
    response = await client.post("/projects", json={
        "source_media_path": str(source_video),
        "name": "ToDelete",
        "source_language": "en",
    })
    assert response.status_code == 200

    project_path = patch_settings.load().projects_dir / "ToDelete.ivoproj"
    assert project_path.exists()

    # 删除
    response = await client.delete("/projects", params={"path": str(project_path)})
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert not project_path.exists()


async def test_delete_project_removes_recent_project_record_when_path_missing(
    client, patch_settings, tmp_path: Path
):
    """Deleting an already-missing project should still clean the project library record."""
    project_path = patch_settings.load().projects_dir / "Ghost.ivoproj"
    patch_settings.add_recent_project(project_path)

    response = await client.delete("/projects", params={"path": str(project_path)})

    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert patch_settings.load().recent_projects == []


async def test_get_nonexistent_project(client):
    """获取不存在的项目"""
    response = await client.get("/projects/detail", params={"path": "C:/nonexistent/path"})
    assert response.status_code == 404
