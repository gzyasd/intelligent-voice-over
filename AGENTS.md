# AGENTS.md

This file provides guidance to Qoder (lingma.aliyun.com) when working with code in this repository.

## 项目概述

Intelligent Voice Over (`ivo`) 是一个本地优先的 Windows 桌面端 AI 视频配音工具。它将英文/日文/韩文视频对白重新配成自然的中文音频，同时支持本地模型流水线和自定义 HTTP API 适配器两种接入模式。

- Python 版本限定：`>=3.10,<3.11`
- 包管理器：`uv`（构建后端为 `hatchling`）
- 桌面 UI：PySide6 (Qt 6)
- 源码包路径：`src/ivo`（安装后以 `ivo` 引用）

## 常用命令

```powershell
# 安装/同步依赖
uv sync --dev

# 一键安装所有本地模型依赖（含 pyannote.audio 独立环境）
.\scripts\setup-local-env.ps1

# 安装本地模型权重（需先接受 Hugging Face 模型条款）
.\scripts\setup-local-models.ps1

# 运行全部测试
uv run pytest

# 运行单个测试文件
uv run pytest tests/test_e2e_mock_pipeline.py -v

# 按名称运行单个测试
uv run pytest -k "test_mock_pipeline" -v

# 代码检查 (lint)
uv run ruff check .

# 类型检查（严格模式）
uv run mypy src

# 环境诊断
uv run ivo doctor

# 启动桌面 UI
uv run python -m ivo.app

# Windows 打包（空运行）
uv run python scripts/build_windows_package.py --dry-run --output-dir dist
```

CI 在 GitHub Actions（`.github/workflows/ci.yml`）上执行：`ruff check .` -> `mypy src` -> `pytest` -> 打包空运行。CI 环境设置 `QT_QPA_PLATFORM=offscreen` 以支持无头 Qt 测试。

## 架构

### 流水线阶段

配音流水线由 `PipelineOrchestrator`（`pipeline/orchestrator.py`）或过程式函数 `run_local_command_preview()`（`pipeline/local_command_preview.py`）编排。每个阶段在 `JobStore`（SQLite）中记录状态，支持通过 `--resume-existing` 断点续跑。

阶段执行顺序：
1. **import** - 将源视频复制到 `.ivoproj/assets/`
2. **audio_extract** - FFmpeg 提取标准化 WAV 到 `assets/extracted_audio.wav`
3. **separation** - 通过本地命令（Demucs）或 HTTP API 分离人声/背景音 -> `work/vocals.wav`、`work/background.wav`
4. **asr** - 通过本地命令（faster-whisper）或 HTTP API 将人声转录为带时间戳的片段
5. **diarization**（可选）- 通过本地命令（pyannote）或 HTTP API 为片段分配说话人 ID
6. **translation** - 通过 HTTP API（如 LM Studio）或 mock 适配器将源文本翻译为目标语言
7. **tts** - 通过本地命令（F5-TTS/CosyVoice）或 HTTP API 逐片段合成目标音频 -> `work/generated_segments/{id}.wav`
8. **export** - FFmpeg 混合背景音 + 延迟对齐的片段音频，添加水印，输出最终 MP4

`local_command_preview.py` 中的 `_run_stage()` 辅助函数负责阶段状态管理和恢复逻辑。每个阶段会先检查 job 记录是否已 `completed`，并尝试从磁盘恢复已有产物，避免重复执行。

### 适配器模式

所有模型集成（本地命令和 HTTP API）都实现 `adapters/base.py` 中定义的统一接口：

- `StageAdapter`（Protocol）- 要求 `stage`、`provider`、`validate_config()` 和 `run(context) -> AdapterResult`
- `AdapterContext` - 携带 `project_path`、`segment_text`、`source_language`、`target_language`、`speaker_id`、`reference_audio_path` 和 `extra` 字典
- `AdapterResult` - 返回 `ok` 布尔值、`payload` 字典和可选的 `AdapterError`

两种适配器后端：
- **LocalCommandAdapter**（`adapters/local.py`）- 用 Jinja2 模板渲染命令参数，运行子进程，读取输出 JSON。使用 `SandboxedEnvironment` + `StrictUndefined`。
- **HttpStageAdapter**（`adapters/http.py`）- 通过 `httpx` 发送 HTTP 请求，使用 JSONPath 表达式（`ApiAdapterProfile.response_mapping`）映射响应。

各阶段有专属适配器封装：`LocalCommandAsrAdapter`、`HttpTtsAdapter`、`HttpTranslationAdapter` 等（位于各自的 `pipeline/*.py` 模块中）。每个流水线阶段模块定义自己的本地命令和 HTTP 适配器对。

### Profile 系统

模型配置由 `examples/` 目录中的 JSON profile 文件驱动：
- **LocalCommandProfile** - 描述子进程命令，包含 Jinja2 模板参数和预期输出 JSON 路径
- **LocalCommandPipelineProfiles** - 打包 separation + asr + 可选 diarization + tts 的 profile 组合
- **ApiAdapterProfile** - 描述 HTTP 方法、URL、请求头、请求模板、响应映射和文件上传字段

默认 profile 解析逻辑（`profile_defaults.py`）：检测到 `nvidia-smi` 时优先使用 GPU profile，否则回退到 CPU profile。`profile_runtime.py` 负责相对于 `--models-dir` 根目录解析模型路径。

### 项目模型

`DubbingProject`（`core/project.py`）是核心领域对象，以 `.ivoproj` 目录形式存储：
```
{project}.ivoproj/
  project.json       - 元数据（名称、语言、源视频路径）
  segments.sqlite    - TimelineStore：DubbingSegment 记录
  jobs.sqlite        - JobStore：阶段执行状态记录
  speakers.json      - SpeakerProfileStore
  settings.json      - ProjectSettingsStore（profile 路径、翻译设置）
  assets/            - 源视频、提取的音频
  work/              - 人声、背景音、生成的片段音频
  renders/           - 最终输出视频、评估报告
```

### 核心领域类型

- `DubbingSegment`（`core/timeline.py`）- 带时间戳的配音片段，包含源/目标文本、说话人、emotion、style_prompt、状态（`pending` -> `approved` -> `rendered`）和 quality_flags。通过 `TimelineStore` 存储在 SQLite 中。
- `SourceLanguage` = `"en" | "ja" | "ko"`，`TargetLanguage` = `"zh"`（硬编码）
- `ExportConfirmation` - 合规闸门，最终导出前必须显式设置 `accepted=True`

### 桌面 UI（PySide6）

入口：`ivo.app` -> `ui/main_window.py` `MainWindow`。UI 为单窗口布局，包含标签页（时间线、模型设置、运行日志）。耗时操作使用 `PipelineWorker`（`ui/workers.py` 中的 QThread 子类），通过 `succeeded`/`failed` 信号避免阻塞主线程。

### 合规层

`compliance/` 模块强制 AI 配音标注：
- `confirmation.py` - 最终导出前的 `ExportConfirmation` 闸门
- `metadata.py` - 将 AI 配音元数据嵌入输出视频
- `watermark.py` - FFmpeg `drawtext` 滤镜实现可见水印（适配 Windows 字体路径）

## 项目约定

- 所有 Pydantic 模型使用 `model_validate()` / `model_dump_json()`（v2 API），不使用 v1 等价方法。
- SQLite 存储（timeline、jobs）使用原生 `sqlite3` + `Row` 工厂，不使用 ORM。
- 适配器中的 Jinja2 模板必须使用 `SandboxedEnvironment` + `StrictUndefined`，禁止使用默认 `Environment`。
- `mypy` 配置为 `strict = true`，所有新代码必须通过严格类型检查。
- Ruff 行长为 100，目标 Python 3.10。
- 测试在 `conftest.py` 中设置 `QT_QPA_PLATFORM=offscreen`，移除会导致 CI 中 GUI 测试失败。
- 测试套件使用 `pytest-qt` 进行 Qt 控件测试（`tests/ui/`）。
- `examples/` 中的 HTTP profile 示例必须使用占位符（`{{ api_key }}`、`YOUR_API_KEY`），禁止写入真实凭据。
- 项目不打包模型权重。依赖模型的功能通过 mock 适配器和 dry-run profile 测试。
