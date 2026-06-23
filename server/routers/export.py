"""导出 API：合规闸门 + 水印 + 元数据"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ivo.compliance.confirmation import ExportConfirmation
from ivo.compliance.metadata import build_ai_dubbing_metadata
from ivo.core.project import DubbingProject
from ivo.pipeline.mix_export import (
    AudioExportRequest,
    ExportRequest,
    SegmentAudio,
    export_dubbed_audio,
    export_dubbed_video,
)

router = APIRouter()


class ExportVideoRequest(BaseModel):
    project_path: str
    watermark_text: str | None = "AI Dubbed"
    accepted: bool = False


class ExportAudioRequest(BaseModel):
    project_path: str
    format: str = "wav"
    accepted: bool = False


@router.post("/video")
def export_video(req: ExportVideoRequest) -> dict[str, Any]:
    """导出配音视频（含合规闸门、水印、AI 元数据）"""
    if not req.accepted:
        raise HTTPException(
            status_code=403,
            detail="必须确认 AI 配音合规声明后才能导出",
        )

    project_path = Path(req.project_path)
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail="项目不存在")

    project = DubbingProject.load(project_path.resolve())

    # 收集导出所需文件
    source_video = project.source_media_path
    if source_video is None:
        raise HTTPException(status_code=400, detail="项目缺少源素材路径")

    background_audio = project_path / "work" / "background.wav"
    if not background_audio.is_file():
        raise HTTPException(status_code=400, detail="背景音文件不存在，请先运行流水线")

    # 收集已合成的片段音频
    segments = project.timeline.list_segments()
    segment_audio: list[SegmentAudio] = []
    for seg in segments:
        if seg.status == "rendered":
            audio_path = project_path / "work" / "generated_segments" / f"{seg.id}.wav"
            if audio_path.is_file():
                segment_audio.append(SegmentAudio(path=audio_path, start_ms=seg.start_ms))

    if not segment_audio:
        raise HTTPException(status_code=400, detail="没有已合成的片段，请先运行 TTS 阶段")

    output_path = project_path / "renders" / "dubbed-output.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = build_ai_dubbing_metadata(
        source_language=project.source_language,
        target_language=project.target_language,
    )

    export_req = ExportRequest(
        source_video=source_video,
        background_audio=background_audio,
        segment_audio=segment_audio,
        output_path=output_path,
        metadata=metadata,
        watermark_text=req.watermark_text,
    )

    try:
        result_path = export_dubbed_video(
            export_req,
            ExportConfirmation(accepted=True),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"导出失败: {exc}") from exc

    return {
        "output_path": str(result_path),
        "segment_count": len(segment_audio),
    }


@router.post("/audio")
def export_audio(req: ExportAudioRequest) -> dict[str, Any]:
    """导出配音音频（纯音频，无视频轨）"""
    if not req.accepted:
        raise HTTPException(
            status_code=403,
            detail="必须确认 AI 配音合规声明后才能导出",
        )

    project_path = Path(req.project_path)
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail="项目不存在")

    project = DubbingProject.load(project_path.resolve())

    background_audio = project_path / "work" / "background.wav"
    if not background_audio.is_file():
        raise HTTPException(status_code=400, detail="背景音文件不存在，请先运行流水线")

    segments = project.timeline.list_segments()
    segment_audio: list[SegmentAudio] = []
    for seg in segments:
        if seg.status == "rendered":
            audio_path = project_path / "work" / "generated_segments" / f"{seg.id}.wav"
            if audio_path.is_file():
                segment_audio.append(SegmentAudio(path=audio_path, start_ms=seg.start_ms))

    if not segment_audio:
        raise HTTPException(status_code=400, detail="没有已合成的片段，请先运行 TTS 阶段")

    ext = "mp3" if req.format == "mp3" else "wav"
    output_path = project_path / "renders" / f"dubbed-output.{ext}"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = build_ai_dubbing_metadata(
        source_language=project.source_language,
        target_language=project.target_language,
    )

    export_req = AudioExportRequest(
        background_audio=background_audio,
        segment_audio=segment_audio,
        output_path=output_path,
        metadata=metadata,
        format=req.format,  # type: ignore[arg-type]
    )

    try:
        result_path = export_dubbed_audio(
            export_req,
            ExportConfirmation(accepted=True),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"导出失败: {exc}") from exc

    return {
        "output_path": str(result_path),
        "segment_count": len(segment_audio),
    }
