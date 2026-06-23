"""Tests for local model service definitions."""

from __future__ import annotations

from pathlib import Path


from ivo.model_services.local_models import (
    ALL_LOCAL_MODEL_SERVICES,
    DEMUCS_SERVICE,
    F5_TTS_SERVICE,
    PYANNOTE_COMMUNITY_1_SERVICE,
    WHISPER_LARGE_V3_TURBO_SERVICE,
    DependencyStatus,
    LocalModelService,
    get_local_service,
    list_local_services_for_stage,
)


def test_dependency_upgrade_requires_semantically_newer_version() -> None:
    assert DependencyStatus(
        package_name="demo",
        import_name="demo",
        status="installed",
        version="1.9.0",
        latest_version="1.10.0",
    ).can_upgrade is True
    assert DependencyStatus(
        package_name="demo",
        import_name="demo",
        status="installed",
        version="2.0.0",
        latest_version="1.10.0",
    ).can_upgrade is False


class TestLocalModelServiceDefinitions:
    def test_all_services_have_required_fields(self) -> None:
        for service in ALL_LOCAL_MODEL_SERVICES:
            assert service.provider_key, f"{service.display_name} missing provider_key"
            assert service.display_name, f"{service.provider_key} missing display_name"
            assert service.stage in ("separation", "asr", "diarization", "tts"), (
                f"{service.provider_key} has invalid stage: {service.stage}"
            )
            assert service.model_dir_name, f"{service.provider_key} missing model_dir_name"

    def test_separation_service_is_demucs(self) -> None:
        assert DEMUCS_SERVICE.stage == "separation"
        assert DEMUCS_SERVICE.provider_key == "demucs"
        assert DEMUCS_SERVICE.commercial_ok is True

    def test_asr_services_include_faster_whisper_variants(self) -> None:
        asr_services = list_local_services_for_stage("asr")
        keys = [s.provider_key for s in asr_services]
        assert "faster-whisper-large-v3" in keys
        assert "faster-whisper-small" in keys
        assert "faster-whisper-tiny" in keys
        assert "whisper-large-v3-turbo" in keys

    def test_diarization_service_is_pyannote(self) -> None:
        assert PYANNOTE_COMMUNITY_1_SERVICE.stage == "diarization"
        assert PYANNOTE_COMMUNITY_1_SERVICE.provider_key == "pyannote-community-1"

    def test_tts_services_include_f5_and_cosyvoice(self) -> None:
        tts_services = list_local_services_for_stage("tts")
        keys = [s.provider_key for s in tts_services]
        assert "f5-tts" in keys
        assert "cosyvoice3" in keys

    def test_f5_tts_has_non_commercial_license_note(self) -> None:
        assert F5_TTS_SERVICE.commercial_ok is False
        assert "非商业" in F5_TTS_SERVICE.license_notes or "NC" in F5_TTS_SERVICE.license_name


class TestLocalModelReadinessCheck:
    def test_check_model_dir_exists(self, tmp_path: Path) -> None:
        model_dir = tmp_path / "separation" / "demucs"
        model_dir.mkdir(parents=True)
        assert DEMUCS_SERVICE.check_model_dir(tmp_path) is True

    def test_check_model_dir_missing(self, tmp_path: Path) -> None:
        assert DEMUCS_SERVICE.check_model_dir(tmp_path) is False

    def test_readiness_check_missing_model(self, tmp_path: Path) -> None:
        result = DEMUCS_SERVICE.readiness_check(tmp_path)
        assert result.status == "missing"
        assert result.model_dir_exists is False
        assert any("not found" in msg.lower() for msg in result.messages)

    def test_readiness_check_ready(self, tmp_path: Path) -> None:
        # Create model dir
        model_dir = tmp_path / "separation" / "demucs"
        model_dir.mkdir(parents=True)
        # Demucs is likely installed in dev environment, so we mock the dep check
        service = LocalModelService(
            provider_key="test-service",
            display_name="Test",
            stage="separation",
            model_dir_name="separation/demucs",
            dependencies=[],  # No deps to check
        )
        result = service.readiness_check(tmp_path)
        assert result.status == "ready"
        assert result.is_ready is True


class TestLocalModelServiceLookup:
    def test_get_existing_service(self) -> None:
        service = get_local_service("demucs")
        assert service is not None
        assert service.provider_key == "demucs"

    def test_get_nonexistent_service(self) -> None:
        assert get_local_service("nonexistent") is None

    def test_list_for_stage(self) -> None:
        asr = list_local_services_for_stage("asr")
        assert len(asr) >= 4
        for s in asr:
            assert s.stage == "asr"

    def test_list_for_unknown_stage(self) -> None:
        assert list_local_services_for_stage("unknown") == []


class TestWhisperLargeV3Turbo:
    def test_uses_transformers_not_faster_whisper(self) -> None:
        dep_names = [d.import_name for d in WHISPER_LARGE_V3_TURBO_SERVICE.dependencies]
        assert "transformers" in dep_names
        assert "faster_whisper" not in dep_names

    def test_has_note_about_format_difference(self) -> None:
        note = WHISPER_LARGE_V3_TURBO_SERVICE.extra_info.get("note", "")
        assert "Transformers" in note or "transformers" in note.lower()


def test_find_pyannote_python_does_not_reuse_main_python_environment_variable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from ivo.model_services.local_models import find_venv_python

    main_python = tmp_path / "main" / "python.exe"
    main_python.parent.mkdir(parents=True)
    main_python.write_bytes(b"python")
    monkeypatch.setenv("IVO_LOCAL_PYTHON", str(main_python))
    monkeypatch.delenv("IVO_PYANNOTE_PYTHON", raising=False)

    assert find_venv_python(".venv-pyannote") != main_python
