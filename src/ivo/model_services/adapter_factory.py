"""Factory to create pipeline Protocol adapters from StageProviderConfig."""

from __future__ import annotations

from typing import Any

from ivo.model_services.provider_config import StageProviderConfig
from ivo.model_services.provider_registry import ProviderRegistry
from ivo.model_services.provider_store import ProviderStore
from ivo.model_services.secret_store import SecretStore


def _coerce_float(value: object, *, default: float) -> float:
    """Parse user-entered numeric config values without crashing the adapter."""
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


def _coerce_int(value: object, *, default: int) -> int:
    """Parse user-entered integer config values without crashing the adapter."""
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


# Built-in command templates for local model providers.
# Each template uses Jinja2 variables rendered by LocalCommandAdapter at runtime.
_LOCAL_COMMAND_TEMPLATES: dict[str, dict[str, Any]] = {
    "demucs": {
        "command": [
            "{{ python_executable }}",
            "examples/local_commands/demucs_separate.py",
            "--audio", "{{ audio_path }}",
            "--vocals-out", "{{ vocals_path }}",
            "--background-out", "{{ background_path }}",
            "--json-out", "{{ output_json_path }}",
            "--model", "htdemucs",
            "--device", "{{ device }}",
            "--two-stems", "vocals",
        ],
        "output_json_path": "{{ project_path }}/demucs-output.json",
    },
    "faster-whisper-large-v3": {
        "command": [
            "{{ python_executable }}",
            "examples/local_commands/faster_whisper_asr.py",
            "--audio", "{{ audio_path }}",
            "--language", "{{ source_language }}",
            "--model", "{{ model_path }}",
            "--device", "{{ device }}",
            "--compute-type", "{{ precision }}",
            "--out", "{{ output_json_path }}",
        ],
        "output_json_path": "{{ project_path }}/faster-whisper-large-v3.json",
    },
    "faster-whisper-small": {
        "command": [
            "{{ python_executable }}",
            "examples/local_commands/faster_whisper_asr.py",
            "--audio", "{{ audio_path }}",
            "--language", "{{ source_language }}",
            "--model", "{{ model_path }}",
            "--device", "{{ device }}",
            "--out", "{{ output_json_path }}",
        ],
        "output_json_path": "{{ project_path }}/faster-whisper-small.json",
    },
    "faster-whisper-tiny": {
        "command": [
            "{{ python_executable }}",
            "examples/local_commands/faster_whisper_asr.py",
            "--audio", "{{ audio_path }}",
            "--language", "{{ source_language }}",
            "--model", "{{ model_path }}",
            "--device", "cpu",
            "--out", "{{ output_json_path }}",
        ],
        "output_json_path": "{{ project_path }}/faster-whisper-tiny.json",
    },
    "pyannote-community-1": {
        "command": [
            "{{ python_executable }}",
            "examples/local_commands/pyannote_diarization.py",
            "--audio", "{{ audio_path }}",
            "--model", "{{ model_path }}",
            "--device", "{{ device }}",
            "--hf-token-env", "{{ hf_token_env }}",
            "--out", "{{ output_json_path }}",
        ],
        "output_json_path": "{{ project_path }}/pyannote-output.json",
    },
    "f5-tts": {
        "command": [
            "{{ python_executable }}",
            "examples/local_commands/f5_tts_command.py",
            "--text", "{{ segment_text }}",
            "--speaker", "{{ speaker_id }}",
            "--audio-out", "{{ output_audio_path }}",
            "--reference-audio", "{{ reference_audio_path }}",
            "--json-out", "{{ output_json_path }}",
        ],
        "output_json_path": "{{ project_path }}/f5-tts-output.json",
    },
    "cosyvoice3": {
        "command": [
            "{{ python_executable }}",
            "examples/local_commands/cosyvoice_tts.py",
            "--text", "{{ segment_text }}",
            "--speaker", "{{ speaker_id }}",
            "--audio-out", "{{ output_audio_path }}",
            "--model-dir", "{{ model_path }}",
            "--reference-audio", "{{ reference_audio_path }}",
            "--json-out", "{{ output_json_path }}",
        ],
        "output_json_path": "{{ project_path }}/cosyvoice3-output.json",
    },
}


class ProviderAdapterFactory:
    """Creates pipeline Protocol adapter instances from StageProviderConfig.

    This factory maps provider configurations to concrete adapter
    implementations that satisfy the existing pipeline Protocol interfaces
    (SeparationAdapter, AsrAdapter, DiarizationAdapter, TranslationAdapter, TtsAdapter).
    """

    def __init__(
        self,
        *,
        registry: ProviderRegistry,
        provider_store: ProviderStore,
        secret_store: SecretStore,
    ) -> None:
        self._registry = registry
        self._provider_store = provider_store
        self._secret_store = secret_store

    def create(self, config: StageProviderConfig) -> Any:
        """Create a pipeline Protocol adapter for the given config.

        Returns an object that implements the appropriate pipeline Protocol
        (SeparationAdapter, AsrAdapter, etc.) based on the config's stage.
        """
        # Resolve API key if needed
        api_key = self._resolve_api_key(config)

        protocol = config.protocol
        stage = config.stage

        # Local providers use existing LocalCommand*Adapter
        if config.kind == "local":
            return self._create_local_adapter(config)

        # API providers: dispatch by protocol
        handler = self._PROTOCOL_HANDLERS.get(protocol)
        if handler is not None:
            return handler(self, config, api_key)

        # Fallback: raise informative error
        raise NotImplementedError(
            f"No adapter implementation for protocol={protocol!r}, stage={stage!r}"
        )

    def _resolve_api_key(self, config: StageProviderConfig) -> str | None:
        if config.account_id is None:
            return None
        account = self._provider_store.get_account(config.account_id)
        if account is None or account.api_key_ref is None:
            return None
        return self._secret_store.load(account.api_key_ref)

    def _create_local_adapter(self, config: StageProviderConfig) -> Any:
        """Create adapter for local model providers."""
        from ivo.adapters.local import LocalCommandProfile

        # Use command from config.extra, or fall back to built-in templates
        command = config.extra.get("command")
        output_json = config.extra.get("output_json_path", "")
        if not command:
            template = _LOCAL_COMMAND_TEMPLATES.get(config.provider_key)
            if template:
                command = template["command"]
                output_json = output_json or template["output_json_path"]

        if not command:
            raise NotImplementedError(
                f"Local provider '{config.provider_key}' has no command template "
                f"and no command in config.extra. "
                f"Register a built-in template in _LOCAL_COMMAND_TEMPLATES "
                f"or provide command in config.extra."
            )

        extra_values = {
            "model_path": config.local_model_path,
            "device": config.device,
            "precision": config.precision,
            **config.extra,
        }
        if not extra_values.get("hf_token_env"):
            extra_values["hf_token_env"] = "HF_TOKEN"

        profile = LocalCommandProfile(
            id=f"local_{config.provider_key}_{config.id}",
            stage=config.stage,
            command=command,  # type: ignore[arg-type]
            output_json_path=str(output_json),
            extra=extra_values,
        )

        if config.stage == "separation":
            from ivo.pipeline.separate_audio import LocalCommandSeparationAdapter
            return LocalCommandSeparationAdapter(profile)
        elif config.stage == "asr":
            from ivo.pipeline.transcribe import LocalCommandAsrAdapter
            return LocalCommandAsrAdapter(profile)
        elif config.stage == "diarization":
            from ivo.pipeline.transcribe import LocalCommandDiarizationAdapter
            return LocalCommandDiarizationAdapter(profile)
        elif config.stage == "tts":
            from ivo.pipeline.synthesize import LocalCommandTtsAdapter
            return LocalCommandTtsAdapter(profile)
        else:
            raise NotImplementedError(
                f"Local adapter not implemented for stage={config.stage!r}"
            )

    def _create_openai_compatible_translation(
        self, config: StageProviderConfig, api_key: str | None
    ) -> Any:
        """Create HttpTranslationAdapter for OpenAI-compatible translation."""
        from ivo.adapters.http import ApiAdapterProfile
        from ivo.pipeline.translate import HttpTranslationAdapter

        request_url = str(config.extra.get("request_url") or "").strip()
        if not request_url:
            account = self._provider_store.get_account(config.account_id or "")
            base_url = account.api_base_url if account else "https://api.openai.com"
            request_url = f"{base_url.rstrip('/')}/v1/chat/completions"
        temperature = _coerce_float(config.extra.get("temperature"), default=0.3)
        max_tokens = _coerce_int(config.extra.get("max_tokens"), default=1000)

        profile = ApiAdapterProfile(
            id=f"openai_compatible_{config.id}",
            stage="translation",
            method="POST",
            url=request_url,
            headers={
                "Authorization": f"Bearer {api_key or ''}",
                "Content-Type": "application/json",
            },
            request_template={
                "model": config.model_name or "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "请将以下 {{source_language}} 台词翻译成{{target_language}}自然中文。"
                            "要求：保留语气和情绪；适合配音口型。输出JSON: target_text, emotion, style_prompt。"
                        ),
                    },
                    {"role": "user", "content": "{{segment_text}}"},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            response_mapping={"content_json": "$.choices[0].message.content"},
        )
        from pathlib import Path
        return HttpTranslationAdapter(profile=profile, project_path=Path("."))

    def _create_anthropic_compatible_translation(
        self, config: StageProviderConfig, api_key: str | None
    ) -> Any:
        """Create adapter for Anthropic-compatible translation."""
        from ivo.adapters.http import ApiAdapterProfile
        from ivo.pipeline.translate import HttpTranslationAdapter

        request_url = str(config.extra.get("request_url") or "").strip()
        if not request_url:
            account = self._provider_store.get_account(config.account_id or "")
            base_url = account.api_base_url if account else "https://api.anthropic.com"
            request_url = f"{base_url.rstrip('/')}/v1/messages"
        anthropic_version = str(config.extra.get("anthropic_version") or "2023-06-01")
        temperature = _coerce_float(config.extra.get("temperature"), default=0.3)
        max_tokens = _coerce_int(config.extra.get("max_tokens"), default=1000)

        profile = ApiAdapterProfile(
            id=f"anthropic_compatible_{config.id}",
            stage="translation",
            method="POST",
            url=request_url,
            headers={
                "x-api-key": api_key or "",
                "anthropic-version": anthropic_version,
                "Content-Type": "application/json",
            },
            request_template={
                "model": config.model_name or "claude-sonnet-4-20250514",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": "{{segment_text}}",
                    }
                ],
                "system": (
                    "请将以下 {{source_language}} 台词翻译成{{target_language}}自然中文。"
                    "要求：保留语气和情绪；适合配音口型。输出JSON: target_text, emotion, style_prompt。"
                ),
            },
            response_mapping={"content_json": "$.content[0].text"},
        )
        from pathlib import Path
        return HttpTranslationAdapter(profile=profile, project_path=Path("."))

    def _create_openai_asr(
        self, config: StageProviderConfig, api_key: str | None
    ) -> Any:
        """Create OpenAI ASR pipeline adapter."""
        from ivo.model_services.adapters.openai_audio import OpenAIAudioProvider
        account = self._provider_store.get_account(config.account_id or "")
        base_url = account.api_base_url if account else "https://api.openai.com"
        provider = OpenAIAudioProvider(
            base_url=base_url,
            api_key=api_key or "",
            model_name=config.model_name or "gpt-4o-transcribe",
            config_id=config.id,
            protocol=config.protocol,
        )
        return provider.to_pipeline_adapter()

    def _create_deepgram_asr(
        self, config: StageProviderConfig, api_key: str | None
    ) -> Any:
        """Create Deepgram ASR pipeline adapter."""
        from ivo.model_services.adapters.deepgram import DeepgramProvider
        is_diarize = config.protocol == "deepgram_diarize"
        provider = DeepgramProvider(
            api_key=api_key or "",
            model_name=config.model_name or "nova-3",
            config_id=config.id,
            protocol=config.protocol,
            diarize=is_diarize,
        )
        return provider.to_pipeline_adapter()

    def _create_audioshake_separation(
        self, config: StageProviderConfig, api_key: str | None
    ) -> Any:
        """Create AudioShake separation pipeline adapter."""
        from ivo.model_services.adapters.audioshake import AudioShakeProvider
        provider = AudioShakeProvider(api_key=api_key or "", config_id=config.id)
        return provider.to_pipeline_adapter()

    def _create_lalalai_separation(
        self, config: StageProviderConfig, api_key: str | None
    ) -> Any:
        """Create LALAL.AI separation pipeline adapter."""
        from ivo.model_services.adapters.lalalai import LalalaiProvider
        provider = LalalaiProvider(api_key=api_key or "", config_id=config.id)
        return provider.to_pipeline_adapter()

    def _create_alibaba_asr(
        self, config: StageProviderConfig, api_key: str | None
    ) -> Any:
        """Create Alibaba Cloud ASR pipeline adapter."""
        from ivo.model_services.adapters.alibaba_asr import AlibabaAsrProvider
        account = self._provider_store.get_account(config.account_id or "")
        base_url = account.api_base_url if account else ""
        provider = AlibabaAsrProvider(
            api_key=api_key or "",
            model_name=config.model_name or "fun-asr",
            config_id=config.id,
            base_url=base_url,
        )
        return provider.to_pipeline_adapter()

    def _create_openai_tts(
        self, config: StageProviderConfig, api_key: str | None
    ) -> Any:
        """Create OpenAI TTS pipeline adapter."""
        from ivo.model_services.adapters.openai_tts import OpenAITtsProvider
        account = self._provider_store.get_account(config.account_id or "")
        base_url = account.api_base_url if account else "https://api.openai.com"
        voice = config.extra.get("voice", "alloy")
        speed = config.extra.get("speed", 1.0)
        provider = OpenAITtsProvider(
            base_url=base_url,
            api_key=api_key or "",
            model_name=config.model_name or "gpt-4o-mini-tts",
            voice=str(voice),
            speed=float(str(speed)),
            config_id=config.id,
        )
        return provider.to_pipeline_adapter()

    def _create_elevenlabs_tts(
        self, config: StageProviderConfig, api_key: str | None
    ) -> Any:
        """Create ElevenLabs TTS pipeline adapter."""
        from ivo.model_services.adapters.elevenlabs_tts import ElevenLabsTtsProvider
        voice_id = config.extra.get("voice_id", "")
        model_id = config.extra.get("model_id", "eleven_multilingual_v2")
        stability = config.extra.get("stability", 0.5)
        similarity_boost = config.extra.get("similarity_boost", 0.75)
        provider = ElevenLabsTtsProvider(
            api_key=api_key or "",
            voice_id=str(voice_id),
            model_id=str(model_id),
            stability=float(str(stability)),
            similarity_boost=float(str(similarity_boost)),
            config_id=config.id,
        )
        return provider.to_pipeline_adapter()

    def _create_alibaba_qwen_tts(
        self, config: StageProviderConfig, api_key: str | None
    ) -> Any:
        """Create Alibaba Qwen-TTS pipeline adapter."""
        from ivo.model_services.adapters.alibaba_qwen_tts import AlibabaQwenTtsProvider
        voice = config.extra.get("voice", "Cherry")
        provider = AlibabaQwenTtsProvider(
            api_key=api_key or "",
            model_name=config.model_name or "qwen3-tts-flash",
            voice=str(voice),
            config_id=config.id,
        )
        return provider.to_pipeline_adapter()

    # Protocol handler registry
    _PROTOCOL_HANDLERS: dict[str, Any] = {}

    def _create_iflytek_lfasr(
        self, config: StageProviderConfig, api_key: str | None
    ) -> Any:
        """Create iFlytek LFASR adapter (P2 – not yet available).

        iFlytek LFASR is a long-audio pre-transcription feature planned for P2.
        It is not intended for short-clip ASR and cannot be used in the pipeline
        until the full upload→merge→getResult workflow is implemented.
        """
        raise NotImplementedError(
            "iFlytek LFASR is a P2 feature for long audio pretranscription. "
            "It is not available as a default short-clip ASR provider."
        )

    @classmethod
    def register_handler(cls, protocol: str, handler: Any) -> None:
        """Register a protocol handler function."""
        cls._PROTOCOL_HANDLERS[protocol] = handler


# Register built-in handlers
ProviderAdapterFactory.register_handler(
    "openai_compatible_translation",
    ProviderAdapterFactory._create_openai_compatible_translation,
)
ProviderAdapterFactory.register_handler(
    "anthropic_compatible_translation",
    ProviderAdapterFactory._create_anthropic_compatible_translation,
)
ProviderAdapterFactory.register_handler(
    "openai_asr",
    ProviderAdapterFactory._create_openai_asr,
)
ProviderAdapterFactory.register_handler(
    "openai_diarize",
    ProviderAdapterFactory._create_openai_asr,
)
ProviderAdapterFactory.register_handler(
    "deepgram_asr",
    ProviderAdapterFactory._create_deepgram_asr,
)
ProviderAdapterFactory.register_handler(
    "deepgram_diarize",
    ProviderAdapterFactory._create_deepgram_asr,
)
ProviderAdapterFactory.register_handler(
    "audioshake_separation",
    ProviderAdapterFactory._create_audioshake_separation,
)
ProviderAdapterFactory.register_handler(
    "lalalai_separation",
    ProviderAdapterFactory._create_lalalai_separation,
)
ProviderAdapterFactory.register_handler(
    "alibaba_asr",
    ProviderAdapterFactory._create_alibaba_asr,
)
ProviderAdapterFactory.register_handler(
    "alibaba_fun_asr",
    ProviderAdapterFactory._create_alibaba_asr,
)
ProviderAdapterFactory.register_handler(
    "alibaba_qwen_asr",
    ProviderAdapterFactory._create_alibaba_asr,
)
ProviderAdapterFactory.register_handler(
    "openai_tts",
    ProviderAdapterFactory._create_openai_tts,
)
ProviderAdapterFactory.register_handler(
    "elevenlabs_tts",
    ProviderAdapterFactory._create_elevenlabs_tts,
)
ProviderAdapterFactory.register_handler(
    "alibaba_qwen_tts",
    ProviderAdapterFactory._create_alibaba_qwen_tts,
)
ProviderAdapterFactory.register_handler(
    "iflytek_lfasr",
    ProviderAdapterFactory._create_iflytek_lfasr,
)
