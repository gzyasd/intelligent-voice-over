"""Tests for provider adapter base protocols and contract."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ivo.model_services.adapters.base import (
    ConnectionValidationResult,
)
from ivo.model_services.adapters.async_job import (
    AsyncJobAdapter,
    AsyncJobHandle,
    AsyncJobStatus,
)


def test_connection_validation_result_model() -> None:
    result = ConnectionValidationResult(
        ok=True,
        provider_id="openai",
        stage="asr",
        model_name="gpt-4o-transcribe",
    )
    assert result.ok is True
    assert result.error_message is None


def test_connection_validation_result_failure() -> None:
    result = ConnectionValidationResult(
        ok=False,
        provider_id="openai",
        stage="asr",
        error_message="Auth failed",
        error_code="AUTH_FAILED",
    )
    assert result.ok is False
    assert result.error_code == "AUTH_FAILED"


def test_async_job_status_enum() -> None:
    assert AsyncJobStatus.PENDING == "pending"
    assert AsyncJobStatus.COMPLETED == "completed"
    assert AsyncJobStatus.FAILED == "failed"
    assert AsyncJobStatus.TIMEOUT == "timeout"


def test_async_job_handle_creation() -> None:
    handle = AsyncJobHandle(
        job_id="job-123",
        provider_id="audioshake",
        stage="separation",
        created_at=1234567890.0,
    )
    assert handle.job_id == "job-123"


class MockAsyncAdapter(AsyncJobAdapter):
    """Concrete implementation for testing the base class."""

    def __init__(self, *, status_sequence: list[AsyncJobStatus]) -> None:
        self.provider_id = "test"
        self.stage = "separation"
        self._status_sequence = status_sequence
        self._call_count = 0

    def create_job(self, **kwargs: object) -> AsyncJobHandle:
        return AsyncJobHandle(
            job_id="test-job",
            provider_id=self.provider_id,
            stage=self.stage,
            created_at=0.0,
        )

    def check_status(self, handle: AsyncJobHandle) -> AsyncJobStatus:
        if self._call_count < len(self._status_sequence):
            status = self._status_sequence[self._call_count]
            self._call_count += 1
            return status
        return AsyncJobStatus.COMPLETED

    def download_result(self, handle: AsyncJobHandle, output_path: Path) -> None:
        output_path.write_bytes(b"test audio data")


def test_async_adapter_execute_success(tmp_path: Path) -> None:
    output = tmp_path / "output.wav"
    adapter = MockAsyncAdapter(
        status_sequence=[AsyncJobStatus.PROCESSING, AsyncJobStatus.COMPLETED]
    )
    with patch("time.sleep"):  # Skip actual sleep
        result = adapter.execute(output)

    assert result.ok is True
    assert output.is_file()


def test_async_adapter_execute_failure(tmp_path: Path) -> None:
    output = tmp_path / "output.wav"
    adapter = MockAsyncAdapter(
        status_sequence=[AsyncJobStatus.PROCESSING, AsyncJobStatus.FAILED]
    )
    with patch("time.sleep"):
        result = adapter.execute(output)

    assert result.ok is False
    assert result.error is not None
    assert "failed" in result.error.message.lower()


def test_adapter_factory_creates_openai_compatible_translation(tmp_path: Path) -> None:
    """Test that factory can create OpenAI-compatible translation adapter."""
    from ivo.model_services.adapter_factory import ProviderAdapterFactory
    from ivo.model_services.provider_config import ProviderAccount, StageProviderConfig
    from ivo.model_services.provider_registry import ProviderRegistry
    from ivo.model_services.provider_store import ProviderStore
    from ivo.model_services.secret_store import SecretStore

    store_dir = tmp_path / "store"
    registry = ProviderRegistry()
    store = ProviderStore(store_dir)
    secrets = SecretStore(store_dir)

    # Set up account and secret
    account = ProviderAccount(
        id="acct-test",
        display_name="Test",
        provider_key="openai",
        kind="api",
        api_base_url="https://api.openai.com",
        api_key_ref="secret-1",
    )
    store.save_account(account)
    secrets.save("secret-1", "sk-test-key")

    config = StageProviderConfig(
        id="stage-translation",
        display_name="OpenAI Translation",
        account_id="acct-test",
        provider_key="openai",
        kind="api",
        stage="translation",
        protocol="openai_compatible_translation",
        model_name="gpt-4o-mini",
    )

    factory = ProviderAdapterFactory(
        registry=registry,
        provider_store=store,
        secret_store=secrets,
    )
    adapter = factory.create(config)
    assert adapter is not None
    assert hasattr(adapter, "translate")


def test_adapter_factory_raises_for_unknown_protocol(tmp_path: Path) -> None:
    from ivo.model_services.adapter_factory import ProviderAdapterFactory
    from ivo.model_services.provider_config import StageProviderConfig
    from ivo.model_services.provider_registry import ProviderRegistry
    from ivo.model_services.provider_store import ProviderStore
    from ivo.model_services.secret_store import SecretStore

    store_dir = tmp_path / "store"
    factory = ProviderAdapterFactory(
        registry=ProviderRegistry(),
        provider_store=ProviderStore(store_dir),
        secret_store=SecretStore(store_dir),
    )
    config = StageProviderConfig(
        id="unknown",
        display_name="Unknown",
        provider_key="unknown",
        kind="api",
        stage="asr",
        protocol="unknown_protocol",
    )
    with pytest.raises(NotImplementedError, match="unknown_protocol"):
        factory.create(config)
