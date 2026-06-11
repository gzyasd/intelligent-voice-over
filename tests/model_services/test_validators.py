"""Tests for model_services validators."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx

from ivo.model_services.validators import (
    ConnectionValidator,
    LocalModelValidator,
    ProviderValidationResult,
)


def test_local_model_missing_directory(tmp_path: Path) -> None:
    result = LocalModelValidator.check_model_directory(tmp_path / "nonexistent")
    assert result.status == "missing"
    assert "不存在" in result.message


def test_local_model_directory_exists(tmp_path: Path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    result = LocalModelValidator.check_model_directory(model_dir)
    assert result.status == "ready"


def test_local_model_path_is_file_not_dir(tmp_path: Path) -> None:
    file_path = tmp_path / "model_file"
    file_path.write_text("not a dir")
    result = LocalModelValidator.check_model_directory(file_path)
    assert result.status == "missing"
    assert "不是目录" in result.message


def test_openai_validation_401_returns_auth_failed() -> None:
    validator = ConnectionValidator(
        base_url="https://api.openai.com",
        api_key="invalid-key",
    )
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401

    with patch("httpx.get", return_value=mock_response):
        result = validator.validate_openai()

    assert result.status == "failed"
    assert "认证失败" in result.message


def test_openai_validation_200_returns_ready() -> None:
    validator = ConnectionValidator(
        base_url="https://api.openai.com",
        api_key="valid-key",
    )
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200

    with patch("httpx.get", return_value=mock_response):
        result = validator.validate_openai()

    assert result.status == "ready"


def test_openai_compatible_lm_studio_unavailable() -> None:
    validator = ConnectionValidator(
        base_url="http://127.0.0.1:1995",
        api_key="lm-studio",
    )

    with patch("httpx.get", side_effect=httpx.ConnectError("Connection refused")):
        result = validator.validate_openai_compatible("lm_studio")

    assert result.status == "failed"
    assert "无法连接" in result.message or "启动" in (result.next_action or "")


def test_openai_compatible_validation_accepts_full_chat_completions_endpoint() -> None:
    validator = ConnectionValidator(
        base_url="http://127.0.0.1:1995/v1/chat/completions",
        api_key="lm-studio",
    )
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200

    with patch("httpx.get", return_value=mock_response) as mock_get:
        result = validator.validate_openai_compatible("openai_compatible_translation")

    assert result.status == "ready"
    mock_get.assert_called_once()
    assert mock_get.call_args.args[0] == "http://127.0.0.1:1995/v1/models"


def test_deepgram_validation_401() -> None:
    validator = ConnectionValidator(
        base_url="https://api.deepgram.com",
        api_key="invalid",
    )
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401

    with patch("httpx.get", return_value=mock_response):
        result = validator.validate_deepgram()

    assert result.status == "failed"


def test_audioshake_validation_200() -> None:
    validator = ConnectionValidator(
        base_url="https://api.audioshake.ai",
        api_key="valid-key",
    )
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200

    with patch("httpx.get", return_value=mock_response):
        result = validator.validate_audioshake()

    assert result.status == "ready"


def test_elevenlabs_validation_401() -> None:
    validator = ConnectionValidator(
        base_url="https://api.elevenlabs.io",
        api_key="invalid",
    )
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401

    with patch("httpx.get", return_value=mock_response):
        result = validator.validate_elevenlabs()

    assert result.status == "failed"


def test_alibaba_validation_403() -> None:
    validator = ConnectionValidator(
        base_url="https://dashscope.aliyuncs.com",
        api_key="invalid",
    )
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403

    with patch("httpx.get", return_value=mock_response):
        result = validator.validate_alibaba_dashscope()

    assert result.status == "failed"


def test_gpu_check_returns_result() -> None:
    result = LocalModelValidator.check_gpu_availability()
    assert isinstance(result, ProviderValidationResult)
    assert result.status in ("ready", "warning")


def test_validation_result_model() -> None:
    result = ProviderValidationResult(
        target_id="test",
        target_kind="account",
        status="ready",
        message="OK",
    )
    assert result.status == "ready"
    assert result.next_action == ""
