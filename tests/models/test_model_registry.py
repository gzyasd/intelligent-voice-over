from __future__ import annotations


def test_model_registry_tracks_profiles_by_stage() -> None:
    from ivo.core.timeline import ModelProfile
    from ivo.models.registry import ModelRegistry

    registry = ModelRegistry()
    profile = ModelProfile(
        id="f5-tts-local",
        stage="tts",
        backend="local",
        name="F5-TTS Local",
        config={"path": "models/f5-tts", "languages": ["zh"]},
    )

    registry.register(profile)

    assert registry.get("f5-tts-local") == profile
    assert registry.list_by_stage("tts") == [profile]
    assert registry.list_by_stage("asr") == []


def test_license_store_confirms_model_license() -> None:
    from ivo.models.licenses import LicenseStore

    store = LicenseStore()

    assert store.is_confirmed("cosyvoice") is False
    store.confirm("cosyvoice")
    assert store.is_confirmed("cosyvoice") is True


def test_model_profile_store_persists_local_model_and_license(tmp_path) -> None:
    from ivo.models.manager import ModelManager, ModelProfileStore

    store_path = tmp_path / "models.json"
    manager = ModelManager.from_store(store_path)
    manager.register_local_model(
        model_id="cosyvoice-local",
        stage="tts",
        name="CosyVoice Local",
        path=tmp_path / "models" / "cosyvoice",
        languages=["zh"],
    )
    manager.licenses.confirm("cosyvoice-local")
    manager.save()

    reloaded = ModelManager.from_store(store_path)

    assert reloaded.registry.get("cosyvoice-local").config["languages"] == ["zh"]
    assert reloaded.can_use("cosyvoice-local") is True
    assert isinstance(ModelProfileStore(store_path).load().profiles, list)
