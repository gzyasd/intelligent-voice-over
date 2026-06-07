from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx

from ivo.core.visual_model_config import VisualStageConfig
from ivo.environment import OptionalDependencyStatus, collect_optional_model_dependencies


@dataclass(frozen=True)
class ModelCandidate:
    stage: str
    name: str
    path: Path
    provider_name: str
    ready: bool
    source: str = "本地目录"


@dataclass(frozen=True)
class StageValidationResult:
    stage: str
    provider: str
    status: str
    message: str


_MODEL_DIR_STAGE_HINTS = {
    "asr": "asr",
    "whisper": "asr",
    "separation": "separation",
    "demucs": "separation",
    "diarization": "diarization",
    "speaker": "diarization",
    "tts": "tts",
    "cosyvoice": "tts",
    "f5": "tts",
    "llm": "translation",
    "qwen": "translation",
    "translation": "translation",
}


def scan_model_candidates(model_root: Path | str) -> list[ModelCandidate]:
    root = Path(model_root).expanduser()
    candidates: dict[tuple[str, str], ModelCandidate] = {}
    for dependency in collect_optional_model_dependencies(root):
        candidate = _candidate_from_dependency(dependency)
        candidates[(candidate.stage, str(candidate.path).casefold())] = candidate

    if root.is_dir():
        for child in root.iterdir():
            if not child.is_dir():
                continue
            stage = _stage_from_dir_name(child.name)
            if stage:
                for model_dir in _direct_model_dirs(child):
                    candidate = ModelCandidate(
                        stage=stage,
                        name=model_dir.name,
                        path=model_dir.resolve(),
                        provider_name=model_dir.name,
                        ready=True,
                    )
                    candidates[(candidate.stage, str(candidate.path).casefold())] = candidate
            else:
                stage = _stage_from_dir_name(child.name)
                if stage:
                    candidate = ModelCandidate(
                        stage=stage,
                        name=child.name,
                        path=child.resolve(),
                        provider_name=child.name,
                        ready=True,
                    )
                    candidates[(candidate.stage, str(candidate.path).casefold())] = candidate

    return sorted(candidates.values(), key=lambda item: (item.stage, not item.ready, item.name.casefold()))


def group_candidates_by_stage(candidates: list[ModelCandidate]) -> dict[str, list[ModelCandidate]]:
    grouped: dict[str, list[ModelCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.stage, []).append(candidate)
    return grouped


def fetch_lm_studio_models(base_url: str, *, timeout: float = 3.0) -> list[str]:
    normalized = base_url.rstrip("/") + "/"
    url = urljoin(normalized, "models")
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        payload = response.json()
    raw_models = payload.get("data", []) if isinstance(payload, dict) else []
    names: list[str] = []
    for item in raw_models:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            names.append(item["id"])
    return names


def validate_stage_config(
    stage: VisualStageConfig,
    model_root: Path | str,
    *,
    lm_studio_models: list[str] | None = None,
) -> StageValidationResult:
    provider = stage.provider_name or stage.label
    if not stage.enabled or stage.service_type == "disabled":
        return StageValidationResult(
            stage=stage.stage,
            provider=provider,
            status="ready",
            message="该阶段已跳过。",
        )
    if stage.service_type == "http":
        return _validate_http_stage(stage, lm_studio_models=lm_studio_models)
    return _validate_local_stage(stage, Path(model_root))


def _candidate_from_dependency(dependency: OptionalDependencyStatus) -> ModelCandidate:
    return ModelCandidate(
        stage=dependency.stage,
        name=dependency.model_dir.name,
        path=dependency.model_dir.resolve(),
        provider_name=dependency.name,
        ready=dependency.model_dir_exists or not dependency.model_dir_required,
        source="推荐模型",
    )


def _direct_model_dirs(stage_dir: Path) -> list[Path]:
    children = [child for child in stage_dir.iterdir() if child.is_dir()]
    return children or [stage_dir]


def _stage_from_dir_name(name: str) -> str | None:
    lowered = name.casefold()
    for hint, stage in _MODEL_DIR_STAGE_HINTS.items():
        if hint in lowered:
            return stage
    return None


def _validate_http_stage(
    stage: VisualStageConfig,
    *,
    lm_studio_models: list[str] | None,
) -> StageValidationResult:
    provider = stage.provider_name or "在线 API"
    if not stage.api_base_url.strip():
        return StageValidationResult(
            stage=stage.stage,
            provider=provider,
            status="missing",
            message="请填写 API 地址。",
        )
    if not stage.api_model.strip():
        return StageValidationResult(
            stage=stage.stage,
            provider=provider,
            status="missing",
            message="请填写模型名称。",
        )
    if lm_studio_models is not None:
        if stage.api_model in lm_studio_models:
            return StageValidationResult(
                stage=stage.stage,
                provider=provider,
                status="ready",
                message="LM Studio 已找到该模型。",
            )
        return StageValidationResult(
            stage=stage.stage,
            provider=provider,
            status="failed",
            message="LM Studio 模型列表中没有这个模型。",
        )
    return StageValidationResult(
        stage=stage.stage,
        provider=provider,
        status="warning",
        message="已填写 API 地址和模型名称，建议读取模型列表后再次校验。",
    )


def _validate_local_stage(stage: VisualStageConfig, model_root: Path) -> StageValidationResult:
    provider = stage.provider_name or stage.label
    raw_path = stage.model_path.strip()
    if not raw_path:
        candidates = group_candidates_by_stage(scan_model_candidates(model_root)).get(stage.stage, [])
        ready = next((candidate for candidate in candidates if candidate.ready), None)
        if ready is not None:
            return StageValidationResult(
                stage=stage.stage,
                provider=ready.provider_name or provider,
                status="ready",
                message=f"已找到模型目录：{ready.path}",
            )
        return StageValidationResult(
            stage=stage.stage,
            provider=provider,
            status="missing",
            message="没有找到模型目录，请先刷新模型目录或手动指定。",
        )
    model_path = Path(raw_path).expanduser()
    if not model_path.is_absolute():
        model_path = model_root / model_path
    if model_path.is_dir():
        return StageValidationResult(
            stage=stage.stage,
            provider=provider,
            status="ready",
            message=f"已找到模型目录：{model_path}",
        )
    return StageValidationResult(
        stage=stage.stage,
        provider=provider,
        status="missing",
        message=f"没有找到模型目录：{model_path}",
    )
