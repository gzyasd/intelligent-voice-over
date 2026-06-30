"""Built-in provider registry with all supported vendors and local models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigField:
    """Form field definition for provider configuration dialogs."""

    name: str
    display_name: str
    field_type: str  # "api_key", "text", "url", "select"
    required: bool = False
    default: str | None = None
    placeholder: str | None = None
    options: tuple[str, ...] | None = None
    validation_pattern: str | None = None


@dataclass(frozen=True)
class ProviderRegistryEntry:
    """A registered provider definition."""

    provider_id: str
    display_name: str
    supported_stages: tuple[str, ...]
    protocols: tuple[str, ...]
    capabilities: frozenset[str] = frozenset()
    requires_api_key: bool = True
    requires_base_url: bool = False
    default_base_url: str | None = None
    config_fields: tuple[ConfigField, ...] = ()
    stage_config_fields: dict[str, tuple[ConfigField, ...]] | None = None
    implemented: bool = True
    mvp_enabled: bool = True
    scenario: str = "default"
    external_docs_url: str = ""


# ---------------------------------------------------------------------------
# API Providers
# ---------------------------------------------------------------------------

_OPENAI = ProviderRegistryEntry(
    provider_id="openai",
    display_name="OpenAI",
    supported_stages=("asr", "diarization", "tts"),
    protocols=(
        "openai_asr",
        "openai_diarize",
        "openai_tts",
    ),
    capabilities=frozenset({"combined_asr_diarization"}),
    requires_api_key=True,
    requires_base_url=False,
    default_base_url="https://api.openai.com",
    config_fields=(
        ConfigField(
            name="api_key",
            display_name="API Key",
            field_type="api_key",
            required=True,
        ),
        ConfigField(
            name="base_url",
            display_name="基础 URL",
            field_type="url",
            required=False,
            default="https://api.openai.com",
            placeholder="https://api.openai.com",
        ),
        ConfigField(
            name="asr_model",
            display_name="ASR 模型",
            field_type="select",
            required=False,
            default="gpt-4o-transcribe-diarize",
            options=(
                "gpt-4o-transcribe-diarize",
                "whisper-1",
                "gpt-4o-transcribe",
                "gpt-4o-mini-transcribe",
            ),
        ),
        ConfigField(
            name="tts_model",
            display_name="TTS 模型",
            field_type="select",
            required=False,
            default="gpt-4o-mini-tts",
            options=("gpt-4o-mini-tts", "tts-1", "tts-1-hd"),
        ),
        ConfigField(
            name="voice",
            display_name="TTS 音色",
            field_type="select",
            required=False,
            default="alloy",
            options=(
                "alloy", "ash", "ballad", "coral", "echo",
                "fable", "onyx", "nova", "sage", "shimmer",
            ),
        ),
    ),
    stage_config_fields={
        "asr": (
            ConfigField("api_key", "API Key", "api_key", required=True),
            ConfigField(
                "base_url",
                "基础 URL",
                "url",
                default="https://api.openai.com",
                placeholder="https://api.openai.com",
            ),
            ConfigField(
                "asr_model",
                "ASR 模型",
                "select",
                default="gpt-4o-transcribe-diarize",
                options=(
                    "gpt-4o-transcribe-diarize",
                    "whisper-1",
                    "gpt-4o-transcribe",
                    "gpt-4o-mini-transcribe",
                ),
            ),
        ),
        "diarization": (
            ConfigField("api_key", "API Key", "api_key", required=True),
            ConfigField(
                "base_url",
                "基础 URL",
                "url",
                default="https://api.openai.com",
                placeholder="https://api.openai.com",
            ),
            ConfigField(
                "diarization_model",
                "说话人识别模型",
                "select",
                default="gpt-4o-transcribe-diarize",
                options=("gpt-4o-transcribe-diarize",),
            ),
            ConfigField(
                "response_format",
                "返回格式",
                "select",
                default="diarized_json",
                options=("diarized_json",),
            ),
        ),
        "tts": (
            ConfigField("api_key", "API Key", "api_key", required=True),
            ConfigField(
                "base_url",
                "基础 URL",
                "url",
                default="https://api.openai.com",
                placeholder="https://api.openai.com",
            ),
            ConfigField(
                "tts_model",
                "TTS 模型",
                "select",
                default="gpt-4o-mini-tts",
                options=("gpt-4o-mini-tts", "tts-1", "tts-1-hd"),
            ),
            ConfigField(
                "voice",
                "TTS 音色",
                "select",
                default="alloy",
                options=(
                    "alloy", "ash", "ballad", "coral", "echo",
                    "fable", "onyx", "nova", "sage", "shimmer",
                ),
            ),
        ),
    },
    external_docs_url="https://platform.openai.com/docs",
)

_DEEPGRAM = ProviderRegistryEntry(
    provider_id="deepgram",
    display_name="Deepgram",
    supported_stages=("asr", "diarization"),
    protocols=("deepgram_asr", "deepgram_diarize"),
    capabilities=frozenset({"combined_asr_diarization"}),
    requires_api_key=True,
    requires_base_url=False,
    default_base_url="https://api.deepgram.com",
    config_fields=(
        ConfigField(
            name="api_key",
            display_name="API Key",
            field_type="api_key",
            required=True,
        ),
        ConfigField(
            name="model",
            display_name="ASR 模型",
            field_type="select",
            required=False,
            default="nova-3",
            options=("nova-3", "nova-2", "enhanced"),
        ),
    ),
    external_docs_url="https://developers.deepgram.com",
)

_AUDIOSHAKE = ProviderRegistryEntry(
    provider_id="audioshake",
    display_name="AudioShake",
    supported_stages=("separation",),
    protocols=("audioshake_separation",),
    requires_api_key=True,
    default_base_url="https://api.audioshake.ai",
    config_fields=(
        ConfigField(
            name="api_key",
            display_name="API Key",
            field_type="api_key",
            required=True,
        ),
    ),
    external_docs_url="https://developer.audioshake.ai",
)

_LALALAI = ProviderRegistryEntry(
    provider_id="lalalai",
    display_name="LALAL.AI",
    supported_stages=("separation",),
    protocols=("lalalai_separation",),
    requires_api_key=True,
    default_base_url="https://www.lalal.ai",
    config_fields=(
        ConfigField(
            name="api_key",
            display_name="License Key",
            field_type="api_key",
            required=True,
        ),
    ),
    external_docs_url="https://www.lalal.ai/api/v1/docs/",
)

_ALIBABA = ProviderRegistryEntry(
    provider_id="alibaba",
    display_name="阿里云百炼",
    supported_stages=("asr",),
    protocols=("alibaba_fun_asr", "alibaba_qwen_asr"),
    requires_api_key=True,
    default_base_url="https://dashscope.aliyuncs.com",
    config_fields=(
        ConfigField(
            name="api_key",
            display_name="DashScope API Key",
            field_type="api_key",
            required=True,
        ),
        ConfigField(
            name="asr_model",
            display_name="ASR 模型",
            field_type="select",
            required=False,
            default="fun-asr",
            options=("fun-asr", "qwen3-asr-flash-filetrans"),
        ),
    ),
    external_docs_url="https://help.aliyun.com/zh/model-studio/asr-model/",
)

_ALIBABA_QWEN_TTS = ProviderRegistryEntry(
    provider_id="alibaba_qwen_tts",
    display_name="阿里云 Qwen-TTS",
    supported_stages=("tts",),
    protocols=("alibaba_qwen_tts",),
    requires_api_key=True,
    default_base_url="https://dashscope.aliyuncs.com",
    config_fields=(
        ConfigField(
            name="api_key",
            display_name="DashScope API Key",
            field_type="api_key",
            required=True,
        ),
        ConfigField(
            name="tts_model",
            display_name="TTS 模型",
            field_type="select",
            required=False,
            default="qwen3-tts-flash",
            options=("qwen3-tts-flash",),
        ),
        ConfigField(
            name="voice",
            display_name="音色",
            field_type="select",
            required=False,
            default="Cherry",
            options=("Cherry", "Serena", "Ethan", "Chelsie"),
        ),
    ),
    external_docs_url="https://help.aliyun.com/zh/model-studio/qwen-tts-api/",
)

_ELEVENLABS = ProviderRegistryEntry(
    provider_id="elevenlabs",
    display_name="ElevenLabs",
    supported_stages=("tts",),
    protocols=("elevenlabs_tts",),
    requires_api_key=True,
    default_base_url="https://api.elevenlabs.io",
    config_fields=(
        ConfigField(
            name="api_key",
            display_name="API Key",
            field_type="api_key",
            required=True,
        ),
        ConfigField(
            name="voice_id",
            display_name="Voice ID",
            field_type="text",
            required=True,
            placeholder="21m00Tcm4TlvDq8ikWAM",
        ),
        ConfigField(
            name="model_id",
            display_name="TTS 模型",
            field_type="select",
            required=False,
            default="eleven_multilingual_v2",
            options=("eleven_multilingual_v2", "eleven_turbo_v2_5"),
        ),
    ),
    external_docs_url="https://elevenlabs.io/docs/api-reference",
)

_OPENAI_COMPATIBLE_TRANSLATION = ProviderRegistryEntry(
    provider_id="openai_compatible_translation",
    display_name="OpenAI 兼容 Chat Completions",
    supported_stages=("translation",),
    protocols=("openai_compatible_translation",),
    requires_api_key=True,
    requires_base_url=True,
    default_base_url="https://api.openai.com",
    config_fields=(
        ConfigField(
            "api_key",
            "API Key",
            "api_key",
            required=False,
            placeholder="本地 LM Studio 通常无需填写",
        ),
        ConfigField(
            "request_url",
            "请求地址",
            "url",
            required=True,
            default="https://api.openai.com/v1/chat/completions",
            placeholder="https://api.openai.com/v1/chat/completions",
        ),
        ConfigField(
            "translation_model",
            "模型名称",
            "text",
            required=True,
            default="gpt-4o-mini",
            placeholder="gpt-4o-mini / LM Studio 模型 ID",
        ),
        ConfigField("temperature", "Temperature", "text", default="0.3"),
        ConfigField("max_tokens", "Max Tokens", "text", default="1000"),
    ),
    external_docs_url="https://platform.openai.com/docs/api-reference/chat/create",
)

_ANTHROPIC = ProviderRegistryEntry(
    provider_id="anthropic",
    display_name="Anthropic",
    supported_stages=("translation",),
    protocols=("anthropic_compatible_translation",),
    requires_api_key=True,
    requires_base_url=True,
    default_base_url="https://api.anthropic.com",
    config_fields=(
        ConfigField(
            name="api_key",
            display_name="API Key",
            field_type="api_key",
            required=True,
        ),
        ConfigField(
            name="base_url",
            display_name="基础 URL",
            field_type="url",
            required=False,
            default="https://api.anthropic.com",
        ),
        ConfigField(
            name="model",
            display_name="模型",
            field_type="text",
            required=False,
            default="claude-sonnet-4-20250514",
        ),
    ),
    mvp_enabled=False,
    external_docs_url="https://docs.anthropic.com/en/api",
)

_ANTHROPIC_COMPATIBLE_TRANSLATION = ProviderRegistryEntry(
    provider_id="anthropic_compatible_translation",
    display_name="Anthropic 兼容 Messages",
    supported_stages=("translation",),
    protocols=("anthropic_compatible_translation",),
    requires_api_key=True,
    requires_base_url=True,
    default_base_url="https://api.anthropic.com",
    config_fields=(
        ConfigField("api_key", "API Key", "api_key", required=True),
        ConfigField(
            "request_url",
            "请求地址",
            "url",
            required=True,
            default="https://api.anthropic.com/v1/messages",
            placeholder="https://api.anthropic.com/v1/messages",
        ),
        ConfigField(
            "translation_model",
            "模型名称",
            "text",
            required=True,
            default="claude-sonnet-4-20250514",
        ),
        ConfigField(
            "anthropic_version",
            "Anthropic-Version",
            "text",
            default="2023-06-01",
        ),
        ConfigField("max_tokens", "Max Tokens", "text", default="1000"),
        ConfigField("temperature", "Temperature", "text", default="0.3"),
    ),
    external_docs_url="https://docs.anthropic.com/en/api/messages",
)

_IFLYTEK = ProviderRegistryEntry(
    provider_id="iflytek",
    display_name="讯飞开放平台",
    supported_stages=("asr",),
    protocols=("iflytek_lfasr",),
    requires_api_key=True,
    default_base_url="https://raasr.xfyun.cn",
    config_fields=(
        ConfigField(
            name="app_id",
            display_name="App ID",
            field_type="text",
            required=True,
        ),
        ConfigField(
            name="secret_key",
            display_name="Secret Key",
            field_type="api_key",
            required=True,
        ),
        ConfigField(
            name="speaker_number",
            display_name="说话人数",
            field_type="text",
            required=False,
            default="2",
        ),
    ),
    implemented=True,
    mvp_enabled=False,
    scenario="long_audio_pretranscription",
    external_docs_url="https://www.xfyun.cn/doc/asr/lfasr/API.html",
)

# ---------------------------------------------------------------------------
# Local Models
# ---------------------------------------------------------------------------

_DEMUCS = ProviderRegistryEntry(
    provider_id="demucs",
    display_name="Demucs (本地)",
    supported_stages=("separation",),
    protocols=("local_demucs",),
    requires_api_key=False,
    config_fields=(
        ConfigField(
            name="local_model_path",
            display_name="模型目录",
            field_type="text",
            required=False,
            default="models/separation/demucs",
        ),
        ConfigField(
            name="device",
            display_name="设备",
            field_type="select",
            required=False,
            default="auto",
            options=("auto", "cuda", "cpu"),
        ),
    ),
    external_docs_url="https://github.com/facebookresearch/demucs",
)

_FASTER_WHISPER_LARGE_V3 = ProviderRegistryEntry(
    provider_id="faster-whisper-large-v3",
    display_name="faster-whisper-large-v3 (本地)",
    supported_stages=("asr",),
    protocols=("local_faster_whisper",),
    requires_api_key=False,
    config_fields=(
        ConfigField(
            name="local_model_path",
            display_name="模型目录",
            field_type="text",
            required=False,
            default="models/asr/faster-whisper-large-v3",
        ),
        ConfigField(
            name="device",
            display_name="设备",
            field_type="select",
            required=False,
            default="auto",
            options=("auto", "cuda", "cpu"),
        ),
        ConfigField(
            name="precision",
            display_name="精度",
            field_type="select",
            required=False,
            default="auto",
            options=("auto", "float16", "int8_float16", "int8"),
        ),
    ),
    external_docs_url="https://huggingface.co/Systran/faster-whisper-large-v3",
)

_FASTER_WHISPER_SMALL = ProviderRegistryEntry(
    provider_id="faster-whisper-small",
    display_name="faster-whisper-small (本地)",
    supported_stages=("asr",),
    protocols=("local_faster_whisper",),
    requires_api_key=False,
    config_fields=(
        ConfigField(
            name="local_model_path",
            display_name="模型目录",
            field_type="text",
            required=False,
            default="models/asr/faster-whisper-small",
        ),
        ConfigField(
            name="device",
            display_name="设备",
            field_type="select",
            required=False,
            default="auto",
            options=("auto", "cuda", "cpu"),
        ),
    ),
    external_docs_url="https://huggingface.co/Systran/faster-whisper-small",
)

_FASTER_WHISPER_TINY = ProviderRegistryEntry(
    provider_id="faster-whisper-tiny",
    display_name="faster-whisper-tiny (本地)",
    supported_stages=("asr",),
    protocols=("local_faster_whisper",),
    requires_api_key=False,
    config_fields=(
        ConfigField(
            name="local_model_path",
            display_name="模型目录",
            field_type="text",
            required=False,
            default="models/asr/faster-whisper-tiny",
        ),
    ),
    external_docs_url="https://huggingface.co/Systran/faster-whisper-tiny",
)

_PYANNOTE_COMMUNITY = ProviderRegistryEntry(
    provider_id="pyannote-community-1",
    display_name="pyannote-community-1 (本地)",
    supported_stages=("diarization",),
    protocols=("local_pyannote",),
    requires_api_key=False,
    config_fields=(
        ConfigField(
            name="local_model_path",
            display_name="模型目录",
            field_type="text",
            required=False,
            default="models/diarization/pyannote-community-1",
        ),
        ConfigField(
            name="hf_token_env",
            display_name="HuggingFace Token 环境变量",
            field_type="text",
            required=False,
            default="HF_TOKEN",
        ),
    ),
    external_docs_url="https://huggingface.co/pyannote/speaker-diarization-community-1",
)

_F5_TTS = ProviderRegistryEntry(
    provider_id="f5-tts",
    display_name="F5-TTS (本地)",
    supported_stages=("tts",),
    protocols=("local_f5_tts",),
    requires_api_key=False,
    config_fields=(
        ConfigField(
            name="local_model_path",
            display_name="模型目录",
            field_type="text",
            required=False,
            default="models/tts/f5-tts",
        ),
        ConfigField(
            name="device",
            display_name="设备",
            field_type="select",
            required=False,
            default="auto",
            options=("auto", "cuda", "cpu"),
        ),
        ConfigField(
            name="runtime_mode",
            display_name="运行模式",
            field_type="select",
            required=False,
            default="worker",
            options=("worker", "subprocess"),
        ),
    ),
    external_docs_url="https://github.com/SWivid/F5-TTS",
)

_COSYVOICE3 = ProviderRegistryEntry(
    provider_id="cosyvoice3",
    display_name="CosyVoice3 (本地)",
    supported_stages=("tts",),
    protocols=("local_cosyvoice",),
    requires_api_key=False,
    config_fields=(
        ConfigField(
            name="local_model_path",
            display_name="模型目录",
            field_type="text",
            required=False,
            default="models/tts/cosyvoice3",
        ),
        ConfigField(
            name="device",
            display_name="设备",
            field_type="select",
            required=False,
            default="auto",
            options=("auto", "cuda", "cpu"),
        ),
    ),
    external_docs_url="https://github.com/FunAudioLLM/CosyVoice",
)


# ---------------------------------------------------------------------------
# Registry class
# ---------------------------------------------------------------------------

_ALL_ENTRIES: tuple[ProviderRegistryEntry, ...] = (
    # API providers
    _OPENAI,
    _OPENAI_COMPATIBLE_TRANSLATION,
    _DEEPGRAM,
    _AUDIOSHAKE,
    _LALALAI,
    _ALIBABA,
    _ALIBABA_QWEN_TTS,
    _ELEVENLABS,
    _ANTHROPIC,
    _ANTHROPIC_COMPATIBLE_TRANSLATION,
    _IFLYTEK,
    # Local models
    _DEMUCS,
    _FASTER_WHISPER_LARGE_V3,
    _FASTER_WHISPER_SMALL,
    _FASTER_WHISPER_TINY,
    _PYANNOTE_COMMUNITY,
    _F5_TTS,
    _COSYVOICE3,
)


class ProviderRegistry:
    """In-memory registry of all known provider definitions."""

    def __init__(self, entries: tuple[ProviderRegistryEntry, ...] | None = None) -> None:
        self._entries: dict[str, ProviderRegistryEntry] = {}
        for entry in entries or _ALL_ENTRIES:
            self._entries[entry.provider_id] = entry

    def list_all(self) -> list[ProviderRegistryEntry]:
        """Return all registered provider entries."""
        return list(self._entries.values())

    def get(self, provider_id: str) -> ProviderRegistryEntry | None:
        """Look up a provider by ID. Returns None if not found."""
        return self._entries.get(provider_id)

    def get_config_fields(
        self, provider_id: str, stage: str
    ) -> tuple[ConfigField, ...]:
        """Return provider config fields scoped to the current pipeline stage."""
        entry = self.get(provider_id)
        if entry is None:
            return ()
        if entry.stage_config_fields and stage in entry.stage_config_fields:
            return entry.stage_config_fields[stage]
        return entry.config_fields

    def list_for_stage(self, stage: str) -> list[ProviderRegistryEntry]:
        """Return providers that support a given stage."""
        return [e for e in self._entries.values() if stage in e.supported_stages]

    def list_mvp_enabled(self) -> list[ProviderRegistryEntry]:
        """Return providers available for MVP (ordinary users)."""
        return [e for e in self._entries.values() if e.mvp_enabled]

    def list_api_providers(self) -> list[ProviderRegistryEntry]:
        """Return API-based providers."""
        return [e for e in self._entries.values() if e.requires_api_key]

    def list_local_providers(self) -> list[ProviderRegistryEntry]:
        """Return local model providers."""
        return [e for e in self._entries.values() if not e.requires_api_key]
