from __future__ import annotations


def test_adapter_profile_store_saves_and_loads_profiles(tmp_path) -> None:
    from ivo.adapters.http import ApiAdapterProfile
    from ivo.adapters.profiles import AdapterProfileStore

    store = AdapterProfileStore(tmp_path / "adapters.json")
    profile = ApiAdapterProfile(
        id="translator",
        stage="translation",
        method="POST",
        url="https://api.example.test/translate",
        headers={"Authorization": "Bearer {{ api_key }}"},
        request_template={"text": "{{ segment_text }}"},
        response_mapping={"text": "$.text"},
    )

    store.save([profile])

    reloaded = AdapterProfileStore(tmp_path / "adapters.json").load()
    assert reloaded == [profile]


def test_adapter_profile_store_returns_empty_list_when_missing(tmp_path) -> None:
    from ivo.adapters.profiles import AdapterProfileStore

    assert AdapterProfileStore(tmp_path / "missing.json").load() == []


def test_adapter_profile_store_rejects_duplicate_ids(tmp_path) -> None:
    import pytest

    from ivo.adapters.http import ApiAdapterProfile
    from ivo.adapters.profiles import AdapterProfileStore

    profile = ApiAdapterProfile(
        id="duplicate",
        stage="translation",
        method="POST",
        url="https://api.example.test/translate",
        headers={},
        request_template={},
        response_mapping={},
    )

    with pytest.raises(ValueError, match="duplicate"):
        AdapterProfileStore(tmp_path / "adapters.json").save([profile, profile])
