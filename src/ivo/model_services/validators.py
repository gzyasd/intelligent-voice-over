"""Connection and local readiness validators for provider configurations."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel


def _openai_models_url_from_endpoint(url: str) -> str:
    """Resolve an OpenAI-compatible models endpoint from a base URL or request URL."""
    root = url.rstrip("/")
    for suffix in ("/v1/chat/completions", "/chat/completions"):
        if root.endswith(suffix):
            return f"{root[: -len(suffix)]}/v1/models"
    if root.endswith("/v1/models"):
        return root
    if root.endswith("/v1"):
        return f"{root}/models"
    return f"{root}/v1/models"


class ProviderValidationResult(BaseModel):
    """Unified validation result for accounts, configs, and schemes."""

    target_id: str
    target_kind: Literal["account", "stage_config", "scheme"]
    status: Literal["ready", "missing", "failed", "warning"]
    message: str
    next_action: str = ""


class ConnectionValidator:
    """Validates API provider connections by making minimal requests."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def _auth_headers(self) -> dict[str, str]:
        """Return Authorization header only when API key is non-empty."""
        if self._api_key:
            return {"Authorization": f"Bearer {self._api_key}"}
        return {}

    def validate_openai(self) -> ProviderValidationResult:
        """Validate OpenAI connection by listing models."""
        try:
            response = httpx.get(
                _openai_models_url_from_endpoint(self._base_url),
                headers=self._auth_headers(),
                timeout=self._timeout,
            )
            if response.status_code == 200:
                return ProviderValidationResult(
                    target_id="openai",
                    target_kind="account",
                    status="ready",
                    message="连接成功",
                )
            if response.status_code == 401:
                return ProviderValidationResult(
                    target_id="openai",
                    target_kind="account",
                    status="failed",
                    message="认证失败",
                    next_action="请检查 API Key",
                )
            return ProviderValidationResult(
                target_id="openai",
                target_kind="account",
                status="failed",
                message=f"HTTP {response.status_code}",
            )
        except httpx.TimeoutException:
            return ProviderValidationResult(
                target_id="openai",
                target_kind="account",
                status="failed",
                message="连接超时",
                next_action="请检查网络或 base URL",
            )
        except httpx.HTTPError as exc:
            return ProviderValidationResult(
                target_id="openai",
                target_kind="account",
                status="failed",
                message=str(exc)[:200],
            )

    def validate_openai_compatible(self, provider_id: str = "openai_compatible") -> ProviderValidationResult:
        """Validate any OpenAI-compatible endpoint."""
        try:
            response = httpx.get(
                _openai_models_url_from_endpoint(self._base_url),
                headers=self._auth_headers(),
                timeout=self._timeout,
            )
            if response.status_code == 200:
                return ProviderValidationResult(
                    target_id=provider_id,
                    target_kind="account",
                    status="ready",
                    message="连接成功",
                )
            if response.status_code == 401:
                return ProviderValidationResult(
                    target_id=provider_id,
                    target_kind="account",
                    status="failed",
                    message="认证失败",
                    next_action="请检查 API Key",
                )
            return ProviderValidationResult(
                target_id=provider_id,
                target_kind="account",
                status="failed",
                message=f"HTTP {response.status_code}",
            )
        except httpx.TimeoutException:
            return ProviderValidationResult(
                target_id=provider_id,
                target_kind="account",
                status="failed",
                message="连接超时",
                next_action="请检查网络或 base URL（LM Studio 是否已启动？）",
            )
        except httpx.ConnectError:
            return ProviderValidationResult(
                target_id=provider_id,
                target_kind="account",
                status="failed",
                message="无法连接服务",
                next_action="请确认服务是否已启动（如 LM Studio）",
            )
        except httpx.HTTPError as exc:
            return ProviderValidationResult(
                target_id=provider_id,
                target_kind="account",
                status="failed",
                message=str(exc)[:200],
            )

    def validate_audioshake(self) -> ProviderValidationResult:
        """Validate AudioShake by listing recent tasks."""
        try:
            response = httpx.get(
                f"{self._base_url}/tasks?skip=0&take=1",
                headers={"x-api-key": self._api_key},
                timeout=self._timeout,
            )
            if response.status_code == 200:
                return ProviderValidationResult(
                    target_id="audioshake",
                    target_kind="account",
                    status="ready",
                    message="连接成功",
                )
            if response.status_code in (401, 403):
                return ProviderValidationResult(
                    target_id="audioshake",
                    target_kind="account",
                    status="failed",
                    message="认证失败",
                    next_action="请检查 API Key",
                )
            return ProviderValidationResult(
                target_id="audioshake",
                target_kind="account",
                status="failed",
                message=f"HTTP {response.status_code}",
            )
        except httpx.HTTPError as exc:
            return ProviderValidationResult(
                target_id="audioshake",
                target_kind="account",
                status="failed",
                message=str(exc)[:200],
            )

    def validate_deepgram(self) -> ProviderValidationResult:
        """Validate Deepgram by listing projects."""
        try:
            response = httpx.get(
                f"{self._base_url}/v1/projects",
                headers={"Authorization": f"Token {self._api_key}"},
                timeout=self._timeout,
            )
            if response.status_code == 200:
                return ProviderValidationResult(
                    target_id="deepgram",
                    target_kind="account",
                    status="ready",
                    message="连接成功",
                )
            if response.status_code == 401:
                return ProviderValidationResult(
                    target_id="deepgram",
                    target_kind="account",
                    status="failed",
                    message="认证失败",
                    next_action="请检查 API Key",
                )
            return ProviderValidationResult(
                target_id="deepgram",
                target_kind="account",
                status="failed",
                message=f"HTTP {response.status_code}",
            )
        except httpx.HTTPError as exc:
            return ProviderValidationResult(
                target_id="deepgram",
                target_kind="account",
                status="failed",
                message=str(exc)[:200],
            )

    def validate_elevenlabs(self) -> ProviderValidationResult:
        """Validate ElevenLabs by getting user info."""
        try:
            response = httpx.get(
                f"{self._base_url}/v1/user",
                headers={"xi-api-key": self._api_key},
                timeout=self._timeout,
            )
            if response.status_code == 200:
                return ProviderValidationResult(
                    target_id="elevenlabs",
                    target_kind="account",
                    status="ready",
                    message="连接成功",
                )
            if response.status_code == 401:
                return ProviderValidationResult(
                    target_id="elevenlabs",
                    target_kind="account",
                    status="failed",
                    message="认证失败",
                    next_action="请检查 API Key",
                )
            return ProviderValidationResult(
                target_id="elevenlabs",
                target_kind="account",
                status="failed",
                message=f"HTTP {response.status_code}",
            )
        except httpx.HTTPError as exc:
            return ProviderValidationResult(
                target_id="elevenlabs",
                target_kind="account",
                status="failed",
                message=str(exc)[:200],
            )

    def validate_alibaba_dashscope(self) -> ProviderValidationResult:
        """Validate Alibaba DashScope by listing tasks.

        Note: This only verifies account connectivity, NOT model-specific
        call permissions. The tasks list endpoint may not be available
        for all account types/regions. Validation passing does not
        guarantee that specific ASR/TTS models are authorized.
        """
        try:
            response = httpx.get(
                f"{self._base_url}/api/v1/tasks",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=self._timeout,
            )
            if response.status_code == 200:
                return ProviderValidationResult(
                    target_id="alibaba",
                    target_kind="account",
                    status="ready",
                    message="连接成功",
                )
            if response.status_code in (401, 403):
                return ProviderValidationResult(
                    target_id="alibaba",
                    target_kind="account",
                    status="failed",
                    message="认证失败",
                    next_action="请检查 DashScope API Key",
                )
            return ProviderValidationResult(
                target_id="alibaba",
                target_kind="account",
                status="failed",
                message=f"HTTP {response.status_code}",
            )
        except httpx.HTTPError as exc:
            return ProviderValidationResult(
                target_id="alibaba",
                target_kind="account",
                status="failed",
                message=str(exc)[:200],
            )

    def validate_lalalai(self) -> ProviderValidationResult:
        """Validate LALAL.AI by checking API connectivity."""
        try:
            response = httpx.request(
                "GET",
                f"{self._base_url}/api/v1/health",
                headers={"Authorization": f"License {self._api_key}"},
                timeout=self._timeout,
            )
            if response.status_code == 200:
                return ProviderValidationResult(
                    target_id="lalalai",
                    target_kind="account",
                    status="ready",
                    message="连接成功",
                )
            if response.status_code in (401, 403):
                return ProviderValidationResult(
                    target_id="lalalai",
                    target_kind="account",
                    status="failed",
                    message="认证失败",
                    next_action="请检查 License Key",
                )
            return ProviderValidationResult(
                target_id="lalalai",
                target_kind="account",
                status="failed",
                message=f"HTTP {response.status_code}",
            )
        except httpx.HTTPError as exc:
            return ProviderValidationResult(
                target_id="lalalai",
                target_kind="account",
                status="failed",
                message=str(exc)[:200],
            )

    def validate_iflytek(self) -> ProviderValidationResult:
        """Validate iFLYTEK connectivity.

        Note: iFLYTEK uses app_id + secret_key HMAC auth, not simple
        bearer tokens. This method only checks basic reachability.
        """
        try:
            response = httpx.request(
                "GET",
                f"{self._base_url}/api/health",
                timeout=self._timeout,
            )
            if response.status_code < 500:
                return ProviderValidationResult(
                    target_id="iflytek",
                    target_kind="account",
                    status="ready",
                    message="服务可达（完整验证需实际调用）",
                )
            return ProviderValidationResult(
                target_id="iflytek",
                target_kind="account",
                status="failed",
                message=f"HTTP {response.status_code}",
            )
        except httpx.HTTPError as exc:
            return ProviderValidationResult(
                target_id="iflytek",
                target_kind="account",
                status="failed",
                message=str(exc)[:200],
            )


class LocalModelValidator:
    """Validates local model readiness."""

    @staticmethod
    def check_model_directory(model_path: Path) -> ProviderValidationResult:
        """Check if a local model directory exists and contains expected files."""
        if not model_path.exists():
            return ProviderValidationResult(
                target_id=str(model_path),
                target_kind="stage_config",
                status="missing",
                message=f"模型目录不存在: {model_path}",
                next_action="请先下载模型",
            )
        if not model_path.is_dir():
            return ProviderValidationResult(
                target_id=str(model_path),
                target_kind="stage_config",
                status="missing",
                message=f"路径不是目录: {model_path}",
                next_action="请检查路径配置",
            )
        return ProviderValidationResult(
            target_id=str(model_path),
            target_kind="stage_config",
            status="ready",
            message="模型目录已找到",
        )

    @staticmethod
    def check_gpu_availability() -> ProviderValidationResult:
        """Check if CUDA GPU is available."""
        try:
            import subprocess

            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                gpu_name = result.stdout.strip().split("\n")[0]
                return ProviderValidationResult(
                    target_id="gpu",
                    target_kind="stage_config",
                    status="ready",
                    message=f"GPU 可用: {gpu_name}",
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return ProviderValidationResult(
            target_id="gpu",
            target_kind="stage_config",
            status="warning",
            message="未检测到 NVIDIA GPU，将使用 CPU 模式",
        )


# --- Provider validation adapter mapping ---

_VALIDATOR_MAP: dict[str, str] = {
    "openai": "validate_openai",
    "openai_asr": "validate_openai",
    "openai_diarize": "validate_openai",
    "openai_tts": "validate_openai",
    "openai_compatible": "validate_openai_compatible",
    "openai_compatible_translation": "validate_openai_compatible",
    "deepgram": "validate_deepgram",
    "deepgram_asr": "validate_deepgram",
    "deepgram_diarize": "validate_deepgram",
    "audioshake": "validate_audioshake",
    "audioshake_separation": "validate_audioshake",
    "lalalai": "validate_lalalai",
    "lalalai_separation": "validate_lalalai",
    "elevenlabs": "validate_elevenlabs",
    "elevenlabs_tts": "validate_elevenlabs",
    "alibaba": "validate_alibaba_dashscope",
    "alibaba_asr": "validate_alibaba_dashscope",
    "alibaba_fun_asr": "validate_alibaba_dashscope",
    "alibaba_qwen_asr": "validate_alibaba_dashscope",
    "alibaba_qwen_tts": "validate_alibaba_dashscope",
    "iflytek": "validate_iflytek",
    "iflytek_lfasr": "validate_iflytek",
    "anthropic": "validate_openai_compatible",
    "anthropic_compatible_translation": "validate_openai_compatible",
}

# Default base URLs per provider (used when caller doesn't supply one)
_PROVIDER_DEFAULT_URLS: dict[str, str] = {
    "openai": "https://api.openai.com",
    "deepgram": "https://api.deepgram.com",
    "audioshake": "https://api.audioshake.ai",
    "lalalai": "https://www.lalal.ai",
    "elevenlabs": "https://api.elevenlabs.io",
    "alibaba": "https://dashscope.aliyuncs.com",
    "iflytek": "https://raasr.xfyun.cn",
    "anthropic": "https://api.anthropic.com",
}

# Base provider IDs that protocol-specific IDs map to for URL resolution
_PROTOCOL_TO_BASE_PROVIDER: dict[str, str] = {
    "openai_asr": "openai",
    "openai_diarize": "openai",
    "openai_tts": "openai",
    "openai_compatible_translation": "openai",
    "deepgram_asr": "deepgram",
    "deepgram_diarize": "deepgram",
    "audioshake_separation": "audioshake",
    "lalalai_separation": "lalalai",
    "elevenlabs_tts": "elevenlabs",
    "alibaba_asr": "alibaba",
    "alibaba_fun_asr": "alibaba",
    "alibaba_qwen_asr": "alibaba",
    "alibaba_qwen_tts": "alibaba",
    "iflytek_lfasr": "iflytek",
    "anthropic_compatible_translation": "anthropic",
}


class _SimpleValidatorAdapter:
    """Lightweight wrapper that calls ConnectionValidator for a given provider."""

    def __init__(
        self,
        *,
        provider_id: str,
        stage: str,
        api_key: str,
        base_url: str = "",
    ) -> None:
        self._provider_id = provider_id
        self._stage = stage
        # Resolve URL: use provided base_url, then check protocol→base mapping,
        # then fall back to default URLs by base provider ID.
        resolved_url = base_url
        if not resolved_url:
            base_provider = _PROTOCOL_TO_BASE_PROVIDER.get(provider_id, provider_id)
            resolved_url = _PROVIDER_DEFAULT_URLS.get(base_provider, "")
        self._validator = ConnectionValidator(
            base_url=resolved_url,
            api_key=api_key,
        )

    def validate_credentials(self) -> _ValidationResultWrapper:
        method_name = _VALIDATOR_MAP.get(self._provider_id)
        if method_name is None:
            return _ValidationResultWrapper(
                ok=False,
                provider_id=self._provider_id,
                stage=self._stage,
                error_code="UNSUPPORTED",
                error_message=f"无法验证供应商: {self._provider_id}",
            )
        method = getattr(self._validator, method_name)
        result: ProviderValidationResult = (
            method() if method_name != "validate_openai_compatible"
            else method(self._provider_id)
        )
        return _ValidationResultWrapper(
            ok=result.status == "ready",
            provider_id=self._provider_id,
            stage=self._stage,
            latency_ms=None,
            error_code=None if result.status == "ready" else result.status.upper(),
            error_message=result.message,
        )


class _ValidationResultWrapper:
    """Simple wrapper matching ConnectionValidationResult interface."""

    def __init__(
        self,
        *,
        ok: bool,
        provider_id: str,
        stage: str,
        latency_ms: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self.ok = ok
        self.provider_id = provider_id
        self.stage = stage
        self.latency_ms = latency_ms
        self.error_code = error_code
        self.error_message = error_message


def create_validator(
    *,
    provider_id: str,
    stage: str,
    api_key: str,
    base_url: str = "",
) -> _SimpleValidatorAdapter:
    """Create a lightweight validator for the given provider."""
    return _SimpleValidatorAdapter(
        provider_id=provider_id,
        stage=stage,
        api_key=api_key,
        base_url=base_url,
    )
