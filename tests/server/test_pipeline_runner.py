from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.mark.asyncio
async def test_subscriber_replays_events_emitted_before_websocket_connects(tmp_path: Path) -> None:
    from server.pipeline_runner import PipelineRunner

    runner = PipelineRunner(str(tmp_path))
    loop = asyncio.get_running_loop()
    runner._loop = loop
    runner._push_event({"stage": "import", "status": "completed"})
    runner._push_event({"stage": "audio_extract", "status": "started"})

    queue = runner.subscribe(loop, after_event_id=0)

    first = await asyncio.wait_for(queue.get(), timeout=1)
    second = await asyncio.wait_for(queue.get(), timeout=1)
    assert first["event_id"] == 1
    assert first["stage"] == "import"
    assert second["event_id"] == 2
    assert second["stage"] == "audio_extract"


@pytest.mark.asyncio
async def test_subscribe_never_starts_pipeline_implicitly(tmp_path: Path, monkeypatch) -> None:
    from server.pipeline_runner import PipelineRunner

    runner = PipelineRunner(str(tmp_path))
    start = MagicMock()
    monkeypatch.setattr(runner, "start", start)

    runner.subscribe(asyncio.get_running_loop())

    start.assert_not_called()


def test_create_runner_keeps_finished_instance_for_event_replay(tmp_path: Path) -> None:
    from server import pipeline_runner

    pipeline_runner.remove_runner(str(tmp_path))
    first = pipeline_runner.create_runner(str(tmp_path))
    first._finished = True

    assert pipeline_runner.create_runner(str(tmp_path)) is first
    pipeline_runner.remove_runner(str(tmp_path))


def test_active_project_paths_only_contains_live_runners(tmp_path: Path, monkeypatch) -> None:
    from server import pipeline_runner

    running_path = tmp_path / "running.ivoproj"
    finished_path = tmp_path / "finished.ivoproj"
    running = SimpleNamespace(project_path=running_path.resolve(), is_running=True)
    finished = SimpleNamespace(project_path=finished_path.resolve(), is_running=False)
    monkeypatch.setattr(
        pipeline_runner,
        "_runners",
        {
            str(running_path.resolve()): running,
            str(finished_path.resolve()): finished,
        },
    )

    assert pipeline_runner.get_active_project_paths() == {running_path.resolve()}


def test_scheme_pipeline_passes_configured_python_paths_to_adapter_factory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from server import dependencies, pipeline_runner
    from ivo.model_services import adapter_factory, scheme_compiler

    main_python = tmp_path / "main" / "python.exe"
    pyannote_python = tmp_path / "pyannote" / "python.exe"
    main_python.parent.mkdir(parents=True)
    pyannote_python.parent.mkdir(parents=True)
    main_python.write_bytes(b"python")
    pyannote_python.write_bytes(b"python")

    store = MagicMock()
    store.get_scheme.return_value = object()
    settings_store = MagicMock()
    settings_store.load.return_value = SimpleNamespace(
        custom_venv_python=main_python,
        custom_pyannote_python=pyannote_python,
    )
    monkeypatch.setattr(dependencies, "get_provider_store", lambda: store)
    monkeypatch.setattr(dependencies, "get_provider_registry", lambda: MagicMock())
    monkeypatch.setattr(dependencies, "get_secret_store", lambda: MagicMock())
    monkeypatch.setattr(dependencies, "get_user_settings_store", lambda: settings_store)

    captured: dict[str, object] = {}

    class FakeFactory:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    class FakeCompiler:
        def __init__(self, **kwargs) -> None:
            pass

        def compile(self, scheme):
            return SimpleNamespace(
                local_profiles=None,
                separation=None,
                asr=None,
                diarization=None,
                translation=None,
                tts=None,
            )

    monkeypatch.setattr(adapter_factory, "ProviderAdapterFactory", FakeFactory)
    monkeypatch.setattr(scheme_compiler, "SchemeRuntimeCompiler", FakeCompiler)

    project = SimpleNamespace(path=tmp_path)
    pipeline_runner._build_adapters_from_project_scheme(project, "scheme-id")

    assert captured["local_python"] == main_python
    assert captured["pyannote_python"] == pyannote_python
