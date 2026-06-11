"""Alibaba Cloud (百炼) ASR provider adapter.

Supports Fun-ASR non-realtime HTTP API and optional Qwen3-ASR.
Both are async tasks requiring create → poll → download result workflow.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx

from ivo.core.timeline import SourceLanguage
from ivo.model_services.adapters.base import ConnectionValidationResult
from ivo.pipeline.transcribe import TranscriptionSegment


class AlibabaAsrProvider:
    """Provider adapter for Alibaba Cloud DashScope ASR APIs."""

    BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
    POLL_INTERVAL_INITIAL = 3.0
    POLL_INTERVAL_MAX = 30.0
    POLL_BACKOFF_FACTOR = 1.5
    POLL_TIMEOUT = 600.0

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = "fun-asr",
        config_id: str = "",
        base_url: str = "",
    ) -> None:
        self.provider_id = "alibaba"
        self.stage = "asr"
        self.protocol = "alibaba_asr"
        self._api_key = api_key
        self._model_name = model_name
        self._config_id = config_id
        self._base_url = (base_url or self.BASE_URL).rstrip("/")

    def validate_credentials(self) -> ConnectionValidationResult:
        """Validate by listing tasks."""
        try:
            response = httpx.get(
                f"{self._base_url}/tasks",
                headers={"Authorization": f"Bearer {self._api_key}"},
                params={"page_no": "1", "page_size": "1"},
                timeout=10.0,
            )
            if response.status_code == 200:
                return ConnectionValidationResult(
                    ok=True,
                    provider_id=self.provider_id,
                    stage=self.stage,
                    model_name=self._model_name,
                )
            if response.status_code in (401, 403):
                return ConnectionValidationResult(
                    ok=False,
                    provider_id=self.provider_id,
                    stage=self.stage,
                    error_message="Invalid API key",
                    error_code="AUTH_FAILED",
                )
            return ConnectionValidationResult(
                ok=False,
                provider_id=self.provider_id,
                stage=self.stage,
                error_message=f"HTTP {response.status_code}",
                error_code="CONNECTION_ERROR",
            )
        except httpx.HTTPError as exc:
            return ConnectionValidationResult(
                ok=False,
                provider_id=self.provider_id,
                stage=self.stage,
                error_message=str(exc)[:200],
                error_code="CONNECTION_ERROR",
            )

    def to_pipeline_adapter(self) -> _AlibabaAsrPipelineAdapter:
        """Return a pipeline-compatible ASR adapter."""
        return _AlibabaAsrPipelineAdapter(self)

    # -- Internal API methods --

    def _submit_task(self, file_url: str) -> str:
        """Submit transcription task and return task_id."""
        body: dict[str, Any]
        if self._model_name == "fun-asr":
            body = {
                "model": "fun-asr",
                "input": {"file_urls": [file_url]},
                "parameters": {
                    "channel_id": [0],
                    "diarization_enabled": True,
                    "speaker_count": 2,
                    "language_hints": ["zh", "en"],
                },
            }
        else:
            # Qwen3-ASR filetrans
            body = {
                "model": self._model_name,
                "input": {"file_url": file_url},
                "parameters": {"language_hints": ["zh", "en"]},
            }

        response = httpx.post(
            f"{self._base_url}/services/audio/asr/transcription",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            },
            json=body,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return str(data["output"]["task_id"])

    def _check_task(self, task_id: str) -> dict[str, Any]:
        """Check task status. Returns full output dict."""
        response = httpx.get(
            f"{self._base_url}/tasks/{task_id}",
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("output", {})  # type: ignore[no-any-return]

    def _poll_until_done(self, task_id: str) -> dict[str, Any]:
        """Poll task until SUCCEEDED or FAILED."""
        interval = self.POLL_INTERVAL_INITIAL
        elapsed = 0.0
        while elapsed < self.POLL_TIMEOUT:
            output = self._check_task(task_id)
            status = output.get("task_status", "")
            if status == "SUCCEEDED":
                return output
            if status == "FAILED":
                raise RuntimeError(f"Alibaba ASR task {task_id} failed")
            time.sleep(interval)
            elapsed += interval
            interval = min(interval * self.POLL_BACKOFF_FACTOR, self.POLL_INTERVAL_MAX)
        raise TimeoutError(f"Alibaba ASR task {task_id} timed out")


class _AlibabaAsrPipelineAdapter:
    """Implements AsrAdapter protocol for Alibaba Cloud ASR."""

    def __init__(self, provider: AlibabaAsrProvider) -> None:
        self._provider = provider

    def transcribe(
        self, audio_path: Path, *, source_language: SourceLanguage
    ) -> list[TranscriptionSegment]:
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)
        # Fun-ASR requires URLs, not local paths.
        # Check if the audio_path is a local Windows path and model needs URL.
        path_str = str(audio_path)
        is_local_path = (
            path_str.startswith(("C:", "D:", "E:", "F:", "G:", "H:"))
            or path_str.startswith("/")
            or path_str.startswith("\\")
        )
        if is_local_path and self._provider._model_name.startswith("fun-asr"):
            raise ValueError(
                f"Fun-ASR 不支持本地文件路径。请先将音频上传到可公网访问的 URL，"
                f"或使用支持本地路径的模型 (如 qwen3-asr-flash)。"
                f"文件: {audio_path}"
            )
        file_url = str(audio_path)
        task_id = self._provider._submit_task(file_url)
        output = self._provider._poll_until_done(task_id)
        return _parse_alibaba_results(output, source_language, self._provider._model_name)


def _parse_alibaba_results(
    output: dict[str, Any],
    source_language: SourceLanguage,
    model_name: str,
) -> list[TranscriptionSegment]:
    """Parse Alibaba ASR results into TranscriptionSegments."""
    segments: list[TranscriptionSegment] = []

    if model_name == "fun-asr":
        # Fun-ASR: results[].transcript_url -> download and parse
        results = output.get("results", [])
        for result in results:
            transcript_url = result.get("transcript_url", "")
            if transcript_url:
                try:
                    response = httpx.get(transcript_url, timeout=30.0)
                    response.raise_for_status()
                    transcript_data = response.json()
                    segs = _parse_fun_asr_transcript(transcript_data, source_language)
                    segments.extend(segs)
                except httpx.HTTPError:
                    pass
    else:
        # Qwen3-ASR: result.transcription_url -> download and parse
        result = output.get("result", {})
        transcription_url = result.get("transcription_url", "")
        if transcription_url:
            try:
                response = httpx.get(transcription_url, timeout=30.0)
                response.raise_for_status()
                transcript_data = response.json()
                segs = _parse_qwen_asr_transcript(transcript_data, source_language)
                segments.extend(segs)
            except httpx.HTTPError:
                pass

    if not segments:
        # Fallback: check for inline text
        text = output.get("text", "")
        if text:
            segments.append(
                TranscriptionSegment(
                    id="0",
                    start_ms=0,
                    end_ms=max(int(output.get("duration", 0) * 1000), 1),
                    source_language=source_language,
                    source_text=str(text).strip(),
                )
            )

    return segments


def _parse_fun_asr_transcript(
    data: dict[str, Any], source_language: SourceLanguage
) -> list[TranscriptionSegment]:
    """Parse Fun-ASR transcript JSON."""
    segments: list[TranscriptionSegment] = []
    transcripts = data.get("transcripts", [])
    for transcript in transcripts:
        sentences = transcript.get("sentences", [])
        for i, sentence in enumerate(sentences):
            segments.append(
                TranscriptionSegment(
                    id=str(i),
                    start_ms=int(sentence.get("begin_time", 0)),
                    end_ms=int(sentence.get("end_time", 1)),
                    source_language=source_language,
                    source_text=str(sentence.get("text", "")).strip(),
                    speaker_id=str(sentence.get("speaker_id", "unknown")),
                )
            )
    return segments


def _parse_qwen_asr_transcript(
    data: dict[str, Any], source_language: SourceLanguage
) -> list[TranscriptionSegment]:
    """Parse Qwen3-ASR transcript JSON."""
    segments: list[TranscriptionSegment] = []
    transcripts = data.get("transcripts", [])
    for transcript in transcripts:
        sentences = transcript.get("sentences", [])
        for i, sentence in enumerate(sentences):
            segments.append(
                TranscriptionSegment(
                    id=str(i),
                    start_ms=int(sentence.get("begin_time", 0)),
                    end_ms=int(sentence.get("end_time", 1)),
                    source_language=source_language,
                    source_text=str(sentence.get("text", "")).strip(),
                )
            )
    return segments
