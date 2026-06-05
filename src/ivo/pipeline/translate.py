from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import httpx
from pydantic import BaseModel

from ivo.adapters.base import AdapterContext
from ivo.adapters.http import ApiAdapterProfile, HttpStageAdapter
from ivo.core.project import DubbingProject
from ivo.core.settings import TranslationSettings
from ivo.core.timeline import DubbingSegment, SourceLanguage, TargetLanguage
from ivo.pipeline.transcribe import TranscriptionSegment


class TranslationResult(BaseModel):
    segment_id: str
    target_text: str
    emotion: str | None = None
    style_prompt: str | None = None


class TranslationAdapter(Protocol):
    def translate(self, segment: TranscriptionSegment, *, prompt: str) -> TranslationResult: ...


class TranslationProviderError(RuntimeError):
    """Raised when a translation provider cannot produce a normalized result."""


class MockTranslationAdapter:
    def __init__(self, translations: dict[str, TranslationResult]) -> None:
        self.translations = translations

    def translate(self, segment: TranscriptionSegment, *, prompt: str) -> TranslationResult:
        if segment.id not in self.translations:
            raise KeyError(f"missing translation for segment: {segment.id}")
        return self.translations[segment.id]


class HttpTranslationAdapter:
    def __init__(
        self,
        profile: ApiAdapterProfile,
        *,
        project_path: Path,
        client: httpx.Client | None = None,
        target_language: TargetLanguage = "zh",
        extra: dict[str, object] | None = None,
    ) -> None:
        self.profile = profile
        self.project_path = project_path
        self.target_language = target_language
        self.extra = extra or {}
        self.adapter = HttpStageAdapter(profile, client=client)

    def translate(self, segment: TranscriptionSegment, *, prompt: str) -> TranslationResult:
        result = self.adapter.run(
            AdapterContext(
                project_path=self.project_path,
                segment_text=segment.source_text,
                source_language=segment.source_language,
                target_language=self.target_language,
                speaker_id=segment.speaker_id,
                extra={
                    "prompt": prompt,
                    "duration_ms": segment.end_ms - segment.start_ms,
                    **self.extra,
                },
            )
        )
        if not result.ok:
            message = result.error.message if result.error is not None else "unknown provider error"
            raise TranslationProviderError(f"{self.profile.id}: {message}")

        payload = _expand_content_json(result.payload, provider_id=self.profile.id)
        target_text = payload.get("target_text", payload.get("text"))
        if not isinstance(target_text, str) or not target_text:
            raise TranslationProviderError(f"{self.profile.id}: missing target_text in response")
        emotion = payload.get("emotion")
        style_prompt = payload.get("style_prompt")
        return TranslationResult(
            segment_id=segment.id,
            target_text=target_text,
            emotion=emotion if isinstance(emotion, str) else None,
            style_prompt=style_prompt if isinstance(style_prompt, str) else None,
        )


def build_translation_prompt(
    segment: TranscriptionSegment | None = None,
    *,
    target_language: TargetLanguage,
    source_language: SourceLanguage | None = None,
    source_text: str | None = None,
    duration_ms: int | None = None,
    speaker_id: str | None = None,
    glossary: dict[str, str] | None = None,
    style_notes: str = "",
    preserve_fillers: bool = True,
    max_length_ratio: float = 1.2,
) -> str:
    if segment is not None:
        source_language = segment.source_language
        source_text = segment.source_text
        duration_ms = segment.end_ms - segment.start_ms
        speaker_id = segment.speaker_id
    if source_language is None or source_text is None or duration_ms is None or speaker_id is None:
        raise ValueError("source_language, source_text, duration_ms and speaker_id are required")

    lines = [
        f"请将以下 {source_language} 台词翻译成{target_language}自然中文。",
        "要求：保留必要语气词、停顿感和人物情绪；中文表达要适合配音，不要书面腔。",
        f"尽量适配原始时长 {duration_ms}ms，译文长度建议不超过原文节奏的 {max_length_ratio:.2f} 倍。",
        f"说话人：{speaker_id}",
    ]
    if style_notes.strip():
        lines.append(f"风格备注：{style_notes.strip()}")
    if preserve_fillers:
        lines.append("语气词策略：保留必要的语气词、口癖、迟疑和停顿，不要机械删减。")
    else:
        lines.append("语气词策略：可删减不影响含义的语气词，让配音更紧凑。")
    if glossary:
        lines.append("术语表：")
        lines.extend(f"- {source} -> {target}" for source, target in sorted(glossary.items()))
    lines.extend(
        [
            "请输出 JSON 对象，字段为 target_text、emotion、style_prompt。",
            f"原文：{source_text}",
        ]
    )
    return "\n".join(lines)


def translate_segments(
    project: DubbingProject,
    source_segments: list[TranscriptionSegment],
    adapter: TranslationAdapter,
) -> list[DubbingSegment]:
    created: list[DubbingSegment] = []
    translation_settings = project.settings.load().translation
    for source_segment in source_segments:
        prompt = build_translation_prompt(
            source_segment,
            target_language=project.target_language,
            glossary=translation_settings.glossary,
            style_notes=_series_style_notes(translation_settings),
            preserve_fillers=translation_settings.preserve_fillers,
            max_length_ratio=translation_settings.max_length_ratio,
        )
        translation = adapter.translate(source_segment, prompt=prompt)
        segment = DubbingSegment(
            id=source_segment.id,
            start_ms=source_segment.start_ms,
            end_ms=source_segment.end_ms,
            speaker_id=source_segment.speaker_id,
            source_language=source_segment.source_language,
            source_text=source_segment.source_text,
            target_language=project.target_language,
            target_text=translation.target_text,
            emotion=translation.emotion,
            style_prompt=translation.style_prompt or translation.emotion,
            status="needs_review",
            quality_flags=source_segment.quality_flags,
        )
        project.timeline.upsert_segment(segment)
        created.append(segment)
    return created


def _series_style_notes(settings: TranslationSettings) -> str:
    presets = {
        "american_drama": "美剧对白：口语、节奏快，避免翻译腔。",
        "japanese_drama": "日剧对白：注意敬语、称呼、停顿和语气词。",
        "korean_drama": "韩剧对白：注意称谓、情绪递进和短句自然。",
        "other": "",
    }
    preset = presets[settings.series_type]
    if settings.translation_style_notes.strip():
        return "\n".join(part for part in [preset, settings.translation_style_notes.strip()] if part)
    return preset


def _expand_content_json(payload: dict[str, object], *, provider_id: str) -> dict[str, object]:
    content_json = payload.get("content_json")
    if content_json is None:
        return payload
    if isinstance(content_json, dict):
        return {**payload, **content_json}
    if not isinstance(content_json, str):
        raise TranslationProviderError(f"{provider_id}: content_json must be a JSON object or string")
    try:
        parsed = json.loads(content_json)
    except json.JSONDecodeError as exc:
        raise TranslationProviderError(f"{provider_id}: content_json is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise TranslationProviderError(f"{provider_id}: content_json must decode to an object")
    return {**payload, **parsed}
