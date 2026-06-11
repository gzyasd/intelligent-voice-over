"""Profile migration: import legacy JSON profiles into the new provider system."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from ivo.model_services.provider_config import (
    DubbingScheme,
    ProviderAccount,
    StageProviderConfig,
)
from ivo.model_services.provider_registry import ProviderRegistry
from ivo.model_services.provider_store import ProviderStore
from ivo.model_services.stages import StageName

# Stage name → protocol keyword fragments for matching
_STAGE_PROTOCOL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "separation": ("separation", "separate"),
    "asr": ("asr", "transcribe"),
    "diarization": ("diarize", "diarization"),
    "translation": ("translation", "translate", "compatible"),
    "tts": ("tts", "synth"),
}


def _resolve_protocol_for_stage(
    provider_key: str, stage: str, registry: ProviderRegistry
) -> str:
    """Resolve the correct protocol for a stage from a provider's protocols."""
    entry = registry.get(provider_key)
    if entry and entry.protocols:
        keywords = _STAGE_PROTOCOL_KEYWORDS.get(stage, (stage,))
        for proto in entry.protocols:
            proto_lower = proto.lower()
            if any(kw in proto_lower for kw in keywords):
                return proto
        # Fallback: return first protocol
        return entry.protocols[0]
    # Fallback for unknown providers
    return f"{provider_key}_{stage}"


def migrate_json_profile(
    profile_path: Path,
    store: ProviderStore,
    *,
    stage: StageName = "translation",
    provider_key: str = "openai_compatible",
    display_name: str | None = None,
) -> StageProviderConfig:
    """Import a legacy HTTP API profile JSON into the provider system.

    The profile is read, parsed, and a new StageProviderConfig is created.
    The original JSON file is NOT deleted.
    """
    if not profile_path.is_file():
        raise FileNotFoundError(f"Profile not found: {profile_path}")

    data = json.loads(profile_path.read_text(encoding="utf-8"))

    config_id = str(uuid.uuid4())[:8]
    name = display_name or profile_path.stem.replace("_", " ").title()

    # Extract base URL and model from profile data
    base_url = data.get("base_url", "")
    model_name = data.get("model", "")
    if not base_url:
        headers = data.get("headers", {})
        base_url = headers.get("base_url", "")

    # Resolve protocol from registry, falling back to name construction
    registry = ProviderRegistry()
    protocol = _resolve_protocol_for_stage(provider_key, stage, registry)

    config = StageProviderConfig(
        id=config_id,
        display_name=name,
        provider_key=provider_key,
        kind="api",
        stage=stage,
        protocol=protocol,
        model_name=model_name,
        extra={"source_profile": str(profile_path)},
    )
    store.save_stage_config(config)

    # Create account without API key (user must re-enter)
    account = ProviderAccount(
        id=config_id,
        display_name=name,
        provider_key=provider_key,
        kind="api",
        api_base_url=base_url,
        extra={"source_profile": str(profile_path)},
    )
    store.save_account(account)

    return config


def create_default_mock_scheme(store: ProviderStore) -> DubbingScheme:
    """Create the default mock scheme if no schemes exist."""
    existing = store.load_schemes()
    if existing:
        return existing[0]

    scheme = DubbingScheme(
        id="default-mock",
        display_name="全自动 Mock 预览",
        description="使用 mock 适配器进行预览，不连接任何外部服务",
        bindings=[],
    )
    store.save_scheme(scheme)
    return scheme


def list_importable_profiles(directory: Path) -> list[Path]:
    """Find legacy JSON profile files that can be imported."""
    if not directory.is_dir():
        return []

    patterns = [
        "http_*_profile*.json",
        "http_translation_*.json",
    ]
    results: list[Path] = []
    for pattern in patterns:
        results.extend(directory.glob(pattern))
    return sorted(set(results))
