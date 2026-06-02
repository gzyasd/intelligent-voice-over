# 智能视频配音 v1 实施计划

> **给后续执行者：** 本计划使用复选框（`- [ ]`）追踪实施进度。

**目标：** 开发一个 Windows 桌面端软件，将英文、日文、韩文视频中的对白重新配成自然的中文配音，并尽量保留原始说话人的音色、语气、情感、节奏、背景音和整体观看体验。

**架构：** 软件采用本地优先的 Python 桌面架构，由 PySide6 界面、可恢复的音视频处理流水线、模型/服务提供商抽象层，以及项目化工作区组成。本地模型和自定义线上 HTTP API 共用同一套阶段接口，使 ASR、翻译、音色克隆/TTS、混音导出等阶段可以自由切换，而不影响界面和时间线数据模型。

**技术栈：** Python 3.10、uv、PySide6、pytest、pydantic、SQLite、FFmpeg；本地模型适配 Whisper/Faster-Whisper 或 WhisperX 类 ASR、Demucs/UVR 类人声分离、pyannote 类说话人分离、CosyVoice/F5-TTS 类中文音色克隆/TTS；线上模型通过可配置 HTTP 适配器接入。

---

## 产品决策

- 产品形态：Windows 桌面端，本地优先。
- 第一版语言范围：英文/日文/韩文视频转中文配音。
- 第一版输出目标：完整中文配音视频，而不是仅导出字幕或单独音轨。
- 工作流：半自动审核流程，支持逐句修改译文、说话人、情绪和时长。
- 本地硬件目标：NVIDIA 显卡，16GB+ 显存，用于高质量本地模式。
- 模型策略：本地模型不默认打包进软件；通过模型管理器让用户下载或选择已有模型路径。
- 线上 API 策略：插件式 HTTP 适配器，支持为 ASR、翻译、TTS、音色克隆等阶段配置 endpoint、headers、请求模板和响应映射。
- 处理模式：快速预览模式和高质量最终导出模式。
- 合规策略：导出前强提醒确认；导出文件必须写入 AI 配音元数据；可见角标水印可选，且文字可自定义。

## 范围边界

- v1 不支持任意语言互译，只覆盖英文/日文/韩文到中文。
- v1 不做口型重定向、改嘴型或视频画面级 lip-sync。
- v1 不做多人协作、云端任务队列、权限管理或商业素材管理。
- v1 不做复杂版权审核系统，仅提供用户确认、元数据标记和可选可见水印。
- v1 即使未安装本地 GPU 模型，也应能通过 mock 模型或线上 API 模式跑通核心流程。

## 建议项目结构

```text
Intelligent-Voice-Over/
  pyproject.toml
  README.md
  docs/
    superpowers/
      plans/
        2026-06-01-intelligent-video-dubbing-v1.md
  src/
    ivo/
      __init__.py
      app.py
      cli.py
      core/
        project.py
        timeline.py
        jobs.py
        settings.py
      adapters/
        base.py
        http.py
        local.py
      pipeline/
        import_video.py
        separate_audio.py
        transcribe.py
        translate.py
        synthesize.py
        mix_export.py
        orchestrator.py
      models/
        registry.py
        manager.py
        licenses.py
      ui/
        main_window.py
        project_wizard.py
        timeline_editor.py
        model_settings.py
        export_dialog.py
      compliance/
        confirmation.py
        watermark.py
        metadata.py
  tests/
    core/
    adapters/
    pipeline/
    compliance/
```

## 公共数据接口

### 项目目录

每个项目保存为一个 `.ivoproj` 目录：

```text
example.ivoproj/
  project.json
  segments.sqlite
  assets/
    source_video.mp4
    extracted_audio.wav
  work/
    vocals.wav
    background.wav
    generated_segments/
  renders/
    preview.mp4
    final.mp4
```

### 核心类型

序列化配置优先使用 pydantic model；运行时对象可使用 dataclass 或 pydantic model。

```python
class DubbingSegment(BaseModel):
    id: str
    start_ms: int
    end_ms: int
    speaker_id: str
    source_language: Literal["en", "ja", "ko"]
    source_text: str
    target_language: Literal["zh"]
    target_text: str
    emotion: str | None = None
    style_prompt: str | None = None
    status: Literal[
        "pending",
        "running",
        "needs_review",
        "approved",
        "failed",
        "rendered",
    ]
    quality_flags: list[str] = []
```

```python
class SpeakerProfile(BaseModel):
    id: str
    display_name: str
    reference_segment_ids: list[str]
    voice_embedding_path: str | None = None
    preferred_tts_profile_id: str | None = None
```

```python
class ModelProfile(BaseModel):
    id: str
    stage: Literal["separation", "asr", "diarization", "translation", "tts", "export"]
    backend: Literal["local", "http", "mock"]
    name: str
    config: dict[str, Any]
```

```python
class ApiAdapterProfile(BaseModel):
    id: str
    stage: str
    method: Literal["GET", "POST"]
    url: str
    headers: dict[str, str]
    request_template: dict[str, Any]
    response_mapping: dict[str, str]
    timeout_seconds: int = 120
```

## 实施任务

### 任务 1：初始化 Python 项目

**文件：**
- 新建：`pyproject.toml`
- 新建：`README.md`
- 新建：`src/ivo/__init__.py`
- 新建：`src/ivo/app.py`
- 新建：`src/ivo/cli.py`
- 新建：`tests/test_smoke.py`

- [x] 使用 Python 3.10 初始化 `uv` Python 包。
- [x] 添加运行时依赖：`pyside6`、`pydantic`、`httpx`、`jinja2`、`jsonpath-ng`、`typer`、`rich`。
- [x] 添加开发依赖：`pytest`、`pytest-qt`、`ruff`、`mypy`。
- [x] 添加 smoke test，验证可以导入 `ivo` 且包版本存在。
- [x] 添加 CLI 命令 `ivo doctor`，输出 Python 版本和 FFmpeg 可用性。
- [x] 运行 `uv run pytest`，确认 smoke test 通过。

### 任务 2：项目存储与时间线模型

**文件：**
- 新建：`src/ivo/core/project.py`
- 新建：`src/ivo/core/timeline.py`
- 新建：`src/ivo/core/jobs.py`
- 测试：`tests/core/test_project.py`
- 测试：`tests/core/test_timeline.py`

- [x] 实现 `.ivoproj` 项目目录创建，包含 `project.json`、`segments.sqlite`、`assets/`、`work/`、`renders/`。
- [x] 实现 `DubbingSegment`、`SpeakerProfile`、`ModelProfile` 和任务状态模型。
- [x] 使用 SQLite 保存片段数据，保证稳定 ID 和毫秒级时间戳。
- [x] 校验片段开始/结束时间非负且顺序正确。
- [x] 支持更新 `target_text`、`speaker_id`、`emotion`、`style_prompt`、`status`、`quality_flags`。
- [x] 测试项目创建、重新加载、片段插入、片段更新和非法时间线拒绝。

### 任务 3：模型/服务适配器抽象

**文件：**
- 新建：`src/ivo/adapters/base.py`
- 新建：`src/ivo/adapters/http.py`
- 新建：`src/ivo/adapters/local.py`
- 测试：`tests/adapters/test_http_adapter.py`
- 测试：`tests/adapters/test_base_contract.py`

- [x] 定义统一阶段适配器接口，包含 `validate_config`、`run` 和结构化结果对象。
- [x] 实现 mock adapter，用于本地开发和 CI。
- [x] 实现 HTTP adapter profile，支持 method、URL、headers、JSON 请求模板、文件上传、超时和响应映射。
- [x] 支持安全变量插值：项目路径、片段文本、源语言、目标语言、说话人 ID、参考音频路径。
- [x] 返回标准化阶段错误，包含 provider 名称、HTTP 状态、响应摘要和是否可重试。
- [x] 测试模板渲染、响应 JSONPath 提取、超时处理和 provider 错误展示。

### 任务 4：视频导入与人声分离

**文件：**
- 新建：`src/ivo/pipeline/import_video.py`
- 新建：`src/ivo/pipeline/separate_audio.py`
- 测试：`tests/pipeline/test_import_video.py`
- 测试：`tests/pipeline/test_separate_audio.py`

- [x] 检测 FFmpeg；缺失时返回清晰的安装提示错误。
- [x] 将源视频复制或链接到项目 `assets/`。
- [x] 提取标准化 WAV 音频，供后续阶段使用。
- [x] 定义人声分离 adapter 接口，先支持 mock 输出，后续接 Demucs/UVR 类本地后端。
- [x] 将 `vocals.wav` 和 `background.wav` 保存到 `work/`。
- [x] 使用测试生成的小型样例媒体测试导入和分离流程。

### 任务 5：ASR、说话人分离与翻译阶段

**文件：**
- 新建：`src/ivo/pipeline/transcribe.py`
- 新建：`src/ivo/pipeline/translate.py`
- 测试：`tests/pipeline/test_transcribe.py`
- 测试：`tests/pipeline/test_translate.py`

- [x] 定义 ASR 输出为带时间戳的源语言片段。
- [x] 定义可选说话人分离输出，将说话人时间范围映射到 ASR 片段。
- [x] 实现 mock ASR 和 mock diarization，保证测试可重复。
- [x] 实现翻译 prompt 构造，要求输出自然中文、保留情绪、必要语气词和适合原时长的表达。
- [x] 将翻译后的片段写入时间线，并标记为 `needs_review`。
- [x] 使用 mock adapter 测试英文、日文、韩文的源语言元数据路径。

### 任务 6：声音参考、TTS 与时长适配

**文件：**
- 新建：`src/ivo/pipeline/synthesize.py`
- 新建：`src/ivo/models/registry.py`
- 新建：`src/ivo/models/manager.py`
- 新建：`src/ivo/models/licenses.py`
- 测试：`tests/pipeline/test_synthesize.py`
- 测试：`tests/models/test_model_registry.py`

- [x] 注册本地模型 profile，但不打包权重。
- [x] 保存模型路径、许可证确认状态、展示名称、支持阶段、支持语言和硬件说明。
- [x] 从已批准的源片段中提取说话人参考音频。
- [x] 实现 mock TTS，生成确定性的测试 WAV 文件。
- [x] 定义时长适配规则：生成音频在容差内则接受；过长则标记 `duration_mismatch`；支持通过调整 style prompt 重新生成。
- [x] 将逐句生成音频保存到 `work/generated_segments/`。
- [x] 测试模型 profile 校验、许可证确认、参考片段查找、TTS 调用和质量标记生成。

### 任务 7：流水线编排与可恢复任务

**文件：**
- 新建：`src/ivo/pipeline/orchestrator.py`
- 修改：`src/ivo/core/jobs.py`
- 测试：`tests/pipeline/test_orchestrator.py`

- [x] 实现任务图：导入、分离、ASR、说话人分离、翻译、审核闸门、合成、混音、导出。
- [x] 持久化任务状态，使失败或中断的项目能从上次完成阶段继续。
- [x] 支持用户编辑文本、情绪、说话人或 style prompt 后逐句重生成。
- [x] 向 UI 发出进度事件，包含阶段名、当前片段、总片段数和最新消息。
- [x] 测试完整 mock 流水线、失败后恢复和逐句重生成。

### 任务 8：混音、导出、元数据与水印

**文件：**
- 新建：`src/ivo/pipeline/mix_export.py`
- 新建：`src/ivo/compliance/confirmation.py`
- 新建：`src/ivo/compliance/metadata.py`
- 新建：`src/ivo/compliance/watermark.py`
- 测试：`tests/pipeline/test_mix_export.py`
- 测试：`tests/compliance/test_metadata_watermark.py`

- [x] 将生成的中文对白与背景音混合。
- [x] 根据片段时间戳放置生成音频。
- [x] 使用 FFmpeg 导出完整视频。
- [x] 最终导出前必须要求用户确认有权处理素材。
- [x] 导出文件必须写入 AI 配音元数据。
- [x] 支持可选可见角标水印，水印文字可自定义。
- [x] 测试元数据生成、可见水印命令构造、导出确认要求和最终输出路径处理。

### 任务 9：PySide6 桌面界面

**文件：**
- 新建：`src/ivo/ui/main_window.py`
- 新建：`src/ivo/ui/project_wizard.py`
- 新建：`src/ivo/ui/timeline_editor.py`
- 新建：`src/ivo/ui/model_settings.py`
- 新建：`src/ivo/ui/export_dialog.py`
- 修改：`src/ivo/app.py`
- 测试：`tests/ui/test_main_window.py`

- [x] 构建主窗口，包含项目打开/创建和任务进度展示。
- [x] 构建项目向导，用于选择源视频、源语言、输出目录和处理模式。
- [x] 构建模型设置页，用于配置本地模型路径和 HTTP adapter profile。
- [x] 构建时间线编辑器，展示源文本、中文文本、说话人、情绪、状态、质量标记和重生成操作。
- [x] 构建导出对话框，包含强确认、必写元数据提示、可选角标开关和自定义角标文本。
- [x] 使用后台 worker，避免长时间流水线任务冻结 UI。
- [x] 使用 `pytest-qt` 测试窗口创建、表单校验、时间线表格渲染和导出确认闸门。

### 任务 10：质量模式与端到端验收

**文件：**
- 修改：`src/ivo/core/settings.py`
- 修改：`src/ivo/pipeline/orchestrator.py`
- 新建：`tests/test_e2e_mock_pipeline.py`

- [x] 定义 `fast_preview` 和 `high_quality_export` 两种处理 profile。
- [x] 快速预览模式使用低成本 provider 和较宽松质量标记。
- [x] 高质量模式要求片段通过审核后才能最终导出，并使用最终 TTS/混音设置。
- [x] 添加 mock 端到端测试：创建项目、导入样例视频、生成翻译片段、合成测试音频、导出视频，并验证元数据配置被应用。
- [x] 在 README 中加入安装、`ivo doctor`、启动 UI、运行测试的说明。

## 验证命令

完成任务前运行：

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
uv run ivo doctor
```

UI 冒烟测试：

```powershell
uv run python -m ivo.app
```

mock 端到端验证：

```powershell
uv run pytest tests/test_e2e_mock_pipeline.py -v
```

## 验收标准

- 用户可以从本地视频文件创建项目。
- 不安装本地 GPU 模型时，mock 流水线也能完整跑通。
- 架构支持每个阶段在 mock、本地模型和 HTTP provider 之间切换。
- 最终合成和导出前，用户可以编辑时间线。
- 未确认素材处理权利时，不能进入最终导出。
- 导出视频必须配置 AI 配音元数据。
- 可见角标水印可选，且文字可自定义。
- 测试覆盖项目存储、adapter、流水线编排、导出合规和基础 UI 行为。

## 实施顺序

1. 初始化项目和 smoke test。
2. 实现项目存储与时间线模型。
3. 实现 adapter contract 和 HTTP adapter。
4. 用 mock provider 跑通完整流水线。
5. 加入 FFmpeg 媒体导入和导出。
6. 加入模型注册表和本地模型管理器。
7. 围绕 mock 流水线构建 PySide6 UI。
8. 逐个阶段接入真实本地模型 adapter。
9. 调优高质量模式并完善验收测试。
10. 补充 Windows 打包和安装文档。

## 风险与缓解

- **音色相似度受说话人和源音频质量影响。** 通过可选参考片段、可编辑 style prompt 和逐句重生成缓解。
- **长视频处理容易中途失败。** 通过持久化任务状态和阶段产物缓解。
- **线上 API schema 差异大。** 通过可配置 HTTP 请求模板和响应映射缓解。
- **本地模型许可证不同。** 通过模型级许可证确认再启用下载或路径配置缓解。
- **平台转码可能丢失元数据。** 通过可选可见角标水印补充强提示。
- **ASR 或说话人分离错误会级联影响后续效果。** 通过时间线审核、说话人编辑和片段级状态标记缓解。

## 后续实现默认值

- 默认源语言：`en`、`ja`、`ko`。
- 默认目标语言：`zh`。
- 默认可见水印文字：`AI Dubbed`。
- 默认首次处理模式：`fast_preview`。
- 默认最终导出模式：`high_quality_export`。
- 默认高质量导出要求：片段状态必须为 `approved` 或 `rendered`。
- 默认项目扩展名：`.ivoproj`。
- 默认处理中生成音频格式：WAV。
- 默认最终视频内音频编码：优先 AAC；如容器不支持，则使用 Opus 或 FFmpeg 推荐兼容编码。

