"""Tests for scheme pipeline execution integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from ivo.model_services.provider_config import (
    DubbingScheme,
    SchemeStageBinding,
    StageProviderConfig,
)
from ivo.model_services.provider_store import ProviderStore
from ivo.model_services.scheme_compiler import (
    SchemeRuntimeCompiler,
)


@pytest.fixture
def tmp_store(tmp_path: Path) -> ProviderStore:
    return ProviderStore(tmp_path / ".ivo-config")


class TestSchemePipelineIntegration:
    def test_scheme_with_no_bindings_returns_empty_compiled(
        self, tmp_store: ProviderStore
    ) -> None:
        """A scheme with no bindings should compile to an empty adapter set."""
        scheme = DubbingScheme(
            id="empty-scheme",
            display_name="Empty",
            bindings=[],
        )

        class _MockFactory:
            def create(self, config: StageProviderConfig) -> object:
                return object()

        class _MockRegistry:
            def get(self, provider_id: str) -> None:
                return None
            def list_all(self) -> list:
                return []

        class _ConfigStore:
            def __init__(self, store: ProviderStore) -> None:
                self._store = store
            def get(self, config_id: str) -> StageProviderConfig:
                result = self._store.get_stage_config(config_id)
                if result is None:
                    raise KeyError(config_id)
                return result

        compiler = SchemeRuntimeCompiler(
            registry=_MockRegistry(),
            config_store=_ConfigStore(tmp_store),
            adapter_factory=_MockFactory(),
        )
        compiled = compiler.compile(scheme)
        assert compiled.separation is None
        assert compiled.asr is None
        assert compiled.diarization is None
        assert compiled.translation is None
        assert compiled.tts is None

    def test_scheme_with_translation_binding(
        self, tmp_store: ProviderStore
    ) -> None:
        """A scheme with a translation binding should compile with translation adapter."""
        config = StageProviderConfig(
            id="trans-cfg",
            display_name="LM Studio",
            provider_key="openai_compatible",
            kind="api",
            stage="translation",
            protocol="openai_compatible_translation",
            model_name="qwen3",
        )
        tmp_store.save_stage_config(config)

        scheme = DubbingScheme(
            id="trans-scheme",
            display_name="Translation Scheme",
            bindings=[
                SchemeStageBinding(stage="translation", stage_config_id="trans-cfg"),
            ],
        )

        class _MockFactory:
            def create(self, cfg: StageProviderConfig) -> str:
                return f"mock-{cfg.protocol}"

        class _MockRegistry:
            def get(self, provider_id: str) -> None:
                return None
            def list_all(self) -> list:
                return []

        class _ConfigStore:
            def __init__(self, store: ProviderStore) -> None:
                self._store = store
            def get(self, config_id: str) -> StageProviderConfig:
                result = self._store.get_stage_config(config_id)
                if result is None:
                    raise KeyError(config_id)
                return result

        compiler = SchemeRuntimeCompiler(
            registry=_MockRegistry(),
            config_store=_ConfigStore(tmp_store),
            adapter_factory=_MockFactory(),
        )
        compiled = compiler.compile(scheme)
        assert compiled.translation is not None
        assert compiled.asr is None

    def test_api_only_scheme_still_works_without_local_profiles(
        self, tmp_store: ProviderStore
    ) -> None:
        """Pure API scheme compiles without local_profiles (will be None)."""
        config = StageProviderConfig(
            id="api-asr",
            display_name="OpenAI ASR",
            provider_key="openai",
            kind="api",
            stage="asr",
            protocol="openai_asr",
        )
        tmp_store.save_stage_config(config)

        scheme = DubbingScheme(
            id="api-only",
            display_name="API Only",
            bindings=[
                SchemeStageBinding(stage="asr", stage_config_id="api-asr"),
            ],
        )

        class _MockFactory:
            def create(self, cfg: StageProviderConfig) -> str:
                return f"adapter-{cfg.protocol}"

        class _MockRegistry:
            def get(self, provider_id: str) -> None:
                return None
            def list_all(self) -> list:
                return []

        class _ConfigStore:
            def __init__(self, store: ProviderStore) -> None:
                self._store = store
            def get(self, config_id: str) -> StageProviderConfig:
                result = self._store.get_stage_config(config_id)
                if result is None:
                    raise KeyError(config_id)
                return result

        compiler = SchemeRuntimeCompiler(
            registry=_MockRegistry(),
            config_store=_ConfigStore(tmp_store),
            adapter_factory=_MockFactory(),
        )
        compiled = compiler.compile(scheme)
        assert compiled.asr is not None
        assert compiled.local_profiles is None

    def test_combined_asr_diarization_deduplicates(
        self, tmp_store: ProviderStore
    ) -> None:
        """OpenAI diarized ASR + same config for diarization should use combined adapter."""
        config = StageProviderConfig(
            id="combined-cfg",
            display_name="OpenAI Diarize",
            provider_key="openai",
            kind="api",
            stage="asr",
            protocol="openai_diarize",
        )
        tmp_store.save_stage_config(config)

        scheme = DubbingScheme(
            id="combined",
            display_name="Combined",
            bindings=[
                SchemeStageBinding(stage="asr", stage_config_id="combined-cfg"),
                SchemeStageBinding(stage="diarization", stage_config_id="combined-cfg"),
            ],
        )

        class _MockFactory:
            def create(self, cfg: StageProviderConfig) -> str:
                return f"asr-{cfg.protocol}"

        class _MockRegistry:
            def get(self, provider_id: str) -> None:
                return None
            def list_all(self) -> list:
                return []

        class _ConfigStore:
            def __init__(self, store: ProviderStore) -> None:
                self._store = store
            def get(self, config_id: str) -> StageProviderConfig:
                result = self._store.get_stage_config(config_id)
                if result is None:
                    raise KeyError(config_id)
                return result

        compiler = SchemeRuntimeCompiler(
            registry=_MockRegistry(),
            config_store=_ConfigStore(tmp_store),
            adapter_factory=_MockFactory(),
        )
        compiled = compiler.compile(scheme)
        assert compiled.asr is not None
        assert compiled.diarization is not None
        # Diarization should be marked as skipped (merged with ASR)
        assert "diarization" in compiled.skipped_stages


class TestMainWindowSchemeIntegration:
    def test_try_compile_returns_none_for_empty_scheme(self, qtbot) -> None:
        """When scheme has no bindings, _try_compile_scheme_adapters returns None."""
        from ivo.ui.main_window import MainWindow

        window = MainWindow()
        qtbot.addWidget(window)

        # Ensure no scheme is applied regardless of disk state
        window.scheme_management_page._current_scheme = None

        result = window._try_compile_scheme_adapters()
        assert result is None

    def test_scheme_management_page_accessible(self, qtbot) -> None:
        """MainWindow should have a scheme_management_page attribute."""
        from ivo.ui.main_window import MainWindow

        window = MainWindow()
        qtbot.addWidget(window)
        assert window.scheme_management_page is not None
