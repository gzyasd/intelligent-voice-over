"""流水线运行管理器：在后台线程中执行流水线，通过队列推送进度事件"""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from typing import Any

from ivo.adapters.http import ApiAdapterProfile
from ivo.adapters.local import CommandExecutionLog, CommandOutputCallback
from ivo.core.project import DubbingProject
from ivo.environment import resolve_executable
from ivo.pipeline.control import PipelineControl
from ivo.pipeline.local_command_preview import (
    LocalCommandPipelineProfiles,
    run_local_command_preview,
)
from ivo.pipeline.progress import PipelineProgressEvent
from ivo.pipeline.separate_audio import HttpSeparationAdapter
from ivo.pipeline.synthesize import HttpTtsAdapter
from ivo.pipeline.transcribe import (
    HttpAsrAdapter,
    HttpDiarizationAdapter,
)
from ivo.pipeline.translate import HttpTranslationAdapter
from ivo.profile_defaults import default_local_command_profiles_path
from ivo.profile_runtime import prepare_local_command_profiles


class PipelineRunner:
    """管理单个项目的流水线执行，支持暂停/恢复和进度推送

    支持多个订阅者：每个 WebSocket 连接通过 subscribe() 获取独立的事件队列，
    既能订阅运行中的流水线，也能在 REST 启动后由 WebSocket 接续订阅。
    """

    def __init__(self, project_path: str) -> None:
        self.project_path = Path(project_path).resolve()
        self.control = PipelineControl()
        self._thread: threading.Thread | None = None
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []
        self._subscribers_lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._error: str | None = None
        self._finished = False
        self._failed_stage: str | None = None
        self._event_history: list[dict[str, Any]] = []
        self._next_event_id = 1

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def is_finished(self) -> bool:
        return self._finished

    @property
    def error(self) -> str | None:
        return self._error

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """启动流水线线程，返回事件队列（首个订阅者）"""
        if self.is_running:
            raise RuntimeError("流水线已在运行中")
        self._loop = loop
        self._error = None
        self._finished = False
        self._failed_stage = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def subscribe(
        self,
        loop: asyncio.AbstractEventLoop,
        *,
        after_event_id: int = 0,
    ) -> asyncio.Queue[dict[str, Any]]:
        """订阅事件流，不隐式启动任务，并补发客户端错过的事件。"""
        self._loop = loop
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        with self._subscribers_lock:
            self._subscribers.append(queue)
            for event in self._event_history:
                if int(event.get("event_id", 0)) > after_event_id:
                    queue.put_nowait(event)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """取消订阅，移除队列"""
        with self._subscribers_lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    def _run(self) -> None:
        """后台线程执行体"""
        try:
            project = DubbingProject.load(self.project_path)
            source_media = project.source_media_path
            if source_media is None:
                raise ValueError("项目缺少源素材路径")

            def progress_callback(event: PipelineProgressEvent) -> None:
                # 记录当前阶段，便于失败时定位
                self._failed_stage = event.stage
                self._push_event(event.model_dump(mode="json"))

            def command_output_callback(log: CommandExecutionLog) -> None:
                self._push_event({
                    "type": "command_log",
                    "stage": log.stage,
                    "provider": log.provider,
                    "command": log.command,
                    "stdout": log.stdout,
                    "stderr": log.stderr,
                    "exit_code": log.exit_code,
                })

            # 从项目设置加载 profile 路径并构建 adapter
            adapters = _build_adapters_from_project_settings(
                project,
                command_output_callback=command_output_callback,
            )

            run_local_command_preview(
                project,
                source_media=source_media,
                profiles=adapters.profiles,
                separation_adapter=adapters.separation,
                asr_adapter=adapters.asr,
                diarization_adapter=adapters.diarization,
                translation_adapter=adapters.translation,
                tts_adapter=adapters.tts,
                ffmpeg_path=adapters.ffmpeg_path,
                progress_callback=progress_callback,
                command_output_callback=command_output_callback,
                control=self.control,
            )
        except Exception as exc:
            self._error = str(exc)
            stage = self._failed_stage or "export"
            stage_labels = {
                "import": "导入素材",
                "audio_extract": "提取音频",
                "separation": "分离人声/背景",
                "asr": "识别字幕",
                "diarization": "识别角色",
                "translation": "翻译改写",
                "tts": "生成配音",
                "export": "合成输出",
            }
            self._push_event({
                "stage": stage,
                "stage_label": stage_labels.get(stage, stage),
                "status": "failed",
                "message": f"流水线执行失败: {exc}",
                "overall_percent": 0,
                "current_item": None,
                "total_items": None,
                "output_path": None,
            })
        finally:
            self._finished = True
            self._push_event({"type": "finished", "error": self._error})

    def _push_event(self, event: dict[str, Any]) -> None:
        """将事件推送到所有订阅者的 asyncio 队列（线程安全）"""
        with self._subscribers_lock:
            stored_event = {**event, "event_id": self._next_event_id}
            self._next_event_id += 1
            self._event_history.append(stored_event)
            subscribers = list(self._subscribers)
        if not self._loop:
            return
        for queue in subscribers:
            try:
                self._loop.call_soon_threadsafe(queue.put_nowait, stored_event)
            except RuntimeError:
                # 事件循环已关闭，忽略
                pass

    def pause(self) -> None:
        self.control.pause()

    def resume(self) -> None:
        self.control.resume()

    def is_paused(self) -> bool:
        return self.control.is_paused()


class _ProjectAdapters:
    """从项目设置解析出的 adapter 集合"""

    def __init__(
        self,
        *,
        profiles: LocalCommandPipelineProfiles | None,
        separation: Any | None,
        asr: Any | None,
        diarization: Any | None,
        translation: Any | None,
        tts: Any | None,
        ffmpeg_path: str | None,
    ) -> None:
        self.profiles = profiles
        self.separation = separation
        self.asr = asr
        self.diarization = diarization
        self.translation = translation
        self.tts = tts
        self.ffmpeg_path = ffmpeg_path


def _build_adapters_from_project_settings(
    project: DubbingProject,
    *,
    command_output_callback: CommandOutputCallback | None = None,
) -> _ProjectAdapters:
    """从项目设置加载 profile 路径并构建所有 adapter

    优先使用项目设置中显式配置的 profile 路径；若未配置，回退到默认
    GPU/CPU profile（用于 separation/asr/tts 本地命令阶段）。
    translation 阶段必须显式配置 HTTP profile，否则使用 MockTranslationAdapter。
    """
    if project.metadata.scheme_id:
        return _build_adapters_from_project_scheme(
            project,
            project.metadata.scheme_id,
            command_output_callback=command_output_callback,
        )

    settings = project.settings.load()
    profile_paths = settings.profiles

    # 解析本地命令 profiles（separation + asr + tts，可选 diarization）
    profiles: LocalCommandPipelineProfiles | None = None
    if profile_paths.local_command_profiles_path:
        profiles_path = Path(profile_paths.local_command_profiles_path)
        if profiles_path.is_file():
            profiles = _load_and_prepare_profiles(profiles_path)
    if profiles is None:
        # 回退到默认 GPU/CPU profile
        default_path = default_local_command_profiles_path()
        if default_path is not None:
            profiles = _load_and_prepare_profiles(default_path)

    # 构建 HTTP adapter（若显式配置了 profile 路径）
    separation_adapter = _build_http_adapter(
        profile_paths.separation_profile_path,
        HttpSeparationAdapter,
        project_path=project.path,
    )
    asr_adapter = _build_http_adapter(
        profile_paths.asr_profile_path,
        HttpAsrAdapter,
        project_path=project.path,
    )
    diarization_adapter = _build_http_adapter(
        profile_paths.diarization_profile_path,
        HttpDiarizationAdapter,
        project_path=project.path,
    )
    translation_adapter = _build_http_adapter(
        profile_paths.translation_profile_path,
        HttpTranslationAdapter,
        project_path=project.path,
        target_language=project.target_language,
    )
    tts_adapter = _build_http_adapter(
        profile_paths.tts_profile_path,
        HttpTtsAdapter,
        project_path=project.path,
    )

    ffmpeg_path = resolve_executable("ffmpeg", env_var="IVO_FFMPEG_PATH")

    return _ProjectAdapters(
        profiles=profiles,
        separation=separation_adapter,
        asr=asr_adapter,
        diarization=diarization_adapter,
        translation=translation_adapter,
        tts=tts_adapter,
        ffmpeg_path=ffmpeg_path,
    )


def _build_adapters_from_project_scheme(
    project: DubbingProject,
    scheme_id: str,
    *,
    command_output_callback: CommandOutputCallback | None = None,
) -> _ProjectAdapters:
    """Compile adapters from the scheme explicitly selected for this project."""
    from server import dependencies
    from ivo.model_services.adapter_factory import ProviderAdapterFactory
    from ivo.model_services.provider_config import StageProviderConfig
    from ivo.model_services.provider_store import ProviderStore
    from ivo.model_services.scheme_compiler import SchemeRuntimeCompiler

    store = dependencies.get_provider_store()
    scheme = store.get_scheme(scheme_id)
    if scheme is None:
        raise ValueError(f"Selected dubbing scheme not found: {scheme_id}")

    class _ConfigStoreAdapter:
        def __init__(self, provider_store: ProviderStore) -> None:
            self._provider_store = provider_store

        def get(self, config_id: str) -> StageProviderConfig:
            config = self._provider_store.get_stage_config(config_id)
            if config is None:
                raise KeyError(f"Stage config not found: {config_id}")
            return config

    registry = dependencies.get_provider_registry()
    user_settings = dependencies.get_user_settings_store().load()
    factory = ProviderAdapterFactory(
        registry=registry,
        provider_store=store,
        secret_store=dependencies.get_secret_store(),
        local_python=user_settings.custom_venv_python,
        pyannote_python=user_settings.custom_pyannote_python,
        command_output_callback=command_output_callback,
    )
    compiler = SchemeRuntimeCompiler(
        registry=registry,
        config_store=_ConfigStoreAdapter(store),
        adapter_factory=factory,
    )
    compiled = compiler.compile(scheme)

    return _ProjectAdapters(
        profiles=compiled.local_profiles,
        separation=compiled.separation,
        asr=compiled.asr,
        diarization=compiled.diarization,
        translation=compiled.translation,
        tts=compiled.tts,
        ffmpeg_path=resolve_executable("ffmpeg", env_var="IVO_FFMPEG_PATH"),
    )


def _load_and_prepare_profiles(profiles_path: Path) -> LocalCommandPipelineProfiles:
    """加载本地命令 profiles JSON 并解析 runtime 路径"""
    raw = json.loads(profiles_path.read_text(encoding="utf-8"))
    profiles = LocalCommandPipelineProfiles.model_validate(raw)
    from server import dependencies

    user_settings = dependencies.get_user_settings_store().load()
    return prepare_local_command_profiles(
        profiles,
        profiles_path=profiles_path,
        python_executable=user_settings.custom_venv_python,
        pyannote_python_executable=user_settings.custom_pyannote_python,
    )


def _build_http_adapter(
    profile_path_str: str,
    adapter_cls: type,
    **kwargs: Any,
) -> Any | None:
    """从 HTTP profile JSON 文件构建 adapter，路径为空或文件不存在返回 None"""
    if not profile_path_str:
        return None
    profile_path = Path(profile_path_str)
    if not profile_path.is_file():
        return None
    profile = ApiAdapterProfile.model_validate(
        json.loads(profile_path.read_text(encoding="utf-8"))
    )
    return adapter_cls(profile, **kwargs)


# 全局运行器注册表（按项目路径索引）
_runners: dict[str, PipelineRunner] = {}
_runners_lock = threading.Lock()


def get_runner(project_path: str) -> PipelineRunner | None:
    """获取指定项目的运行器（如存在）"""
    return _runners.get(str(Path(project_path).resolve()))


def get_active_project_paths() -> set[Path]:
    """Return resolved project paths whose pipeline thread is still alive."""
    with _runners_lock:
        return {
            runner.project_path.resolve()
            for runner in _runners.values()
            if runner.is_running
        }


def get_paused_project_paths() -> set[Path]:
    """Return resolved project paths whose pipeline is currently paused."""
    with _runners_lock:
        return {
            runner.project_path.resolve()
            for runner in _runners.values()
            if runner.is_running and runner.is_paused()
        }


def create_runner(project_path: str) -> PipelineRunner:
    """为项目创建运行器（若已存在且仍在运行则返回现有的）"""
    key = str(Path(project_path).resolve())
    with _runners_lock:
        existing = _runners.get(key)
        if existing is not None:
            return existing
        runner = PipelineRunner(project_path)
        _runners[key] = runner
        return runner


def remove_runner(project_path: str) -> None:
    """移除已完成的运行器"""
    key = str(Path(project_path).resolve())
    with _runners_lock:
        _runners.pop(key, None)


def cleanup_finished_runner(project_path: str) -> None:
    """仅当 runner 已完成时移除，运行中保留"""
    key = str(Path(project_path).resolve())
    with _runners_lock:
        runner = _runners.get(key)
        if runner is not None and (runner.is_finished or not runner.is_running):
            _runners.pop(key, None)
