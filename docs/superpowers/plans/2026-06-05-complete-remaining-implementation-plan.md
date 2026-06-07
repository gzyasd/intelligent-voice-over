# 智能视频配音剩余完整开发 Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从当前已跑通 20 秒真实本地 F5-TTS 预览的状态继续，把 Intelligent Voice Over 推进到可长期使用、可发布、可复现、可评估的开源 Windows 桌面软件。

**Architecture:** 继续坚持本地优先、adapter 优先、项目化工作区和可恢复流水线。真实模型、线上 API、UI 和质量评估都通过统一阶段合约接入，避免把某个模型硬编码进核心流程。

**Tech Stack:** Python 3.10、uv、PySide6、pytest、ruff、mypy、SQLite、FFmpeg、Demucs、faster-whisper、F5-TTS、CosyVoice、pyannote.audio、OpenAI-compatible HTTP API、GitHub Actions。

---

## 当前基线

本计划以 2026-06-05 的 `codex/complete-remaining-roadmap` 分支为基线。

已经完成并验证：

- v1 工程骨架、mock 端到端流水线、项目目录、SQLite 时间线、任务状态、导出合规闸门。
- 本地命令 adapter、HTTP adapter、profile 校验、readiness 检查、模型诊断命令。
- 桌面 UI 基础流程、时间线编辑、单句重生成、导出对话框、mock/local preview 入口。
- 真实 20 秒日语视频链路：Demucs CPU 分离、faster-whisper small CPU/int8 ASR、F5-TTS CPU 真实生成、混音和 MP4 导出。
- 最新本地验证：`uv run pytest` 223 passed、`uv run ruff check .` 通过、`uv run mypy src` 通过。
- 最新 GitHub CI 已通过。

当前整体完成度估算：

- 工程基础和测试底座：85%-90%。
- 真实本地模型最小链路：65%-70%。
- 桌面产品可用性：55%-65%。
- 长视频生产稳定性：35%-45%。
- 发布级完整度：70%-75%。

必须保持的仓库规则：

- 不提交 `测试视频/`、真实影视片段、生成视频、音频片段、模型权重、API key、token。
- `.gitignore` 中的 `models/`、`sample_media/`、`scratch/`、`测试视频/`、`*.mp4`、`*.wav` 等规则不得放松。
- 每个可验证阶段都要 commit/push，不等所有功能完成才上传。
- 每个代码任务先写失败测试，再实现，再跑目标测试和全量质量检查。

## 剩余任务总览

| 优先级 | 任务 | 完成后获得的能力 |
| --- | --- | --- |
| P0 | 真实样片评估资产和验收矩阵 | 每轮模型改动都有可比较结果 |
| P0 | CosyVoice 真实本地 TTS | 获得许可证更适合开源/商用评估的 TTS 路线 |
| P0 | 线上 API 全阶段真实验证 | 用户可不用本地重模型也能跑完整流程 |
| P0 | UI 模型配置和运行日志 | 用户能在桌面端配置 profile、检查环境、定位错误 |
| P1 | 说话人分离和角色音色绑定 | 多角色剧集能维持角色一致性 |
| P1 | 翻译质量、术语表和语气控制 | 美剧/日剧/韩剧对白更自然 |
| P1 | TTS 时长对齐和自动重试 | 配音更贴合原片节奏 |
| P1 | 长视频恢复和批处理加固 | 1-3 分钟到整集级别更稳定 |
| P2 | GPU/性能 profile | 真实模型速度可控 |
| P2 | Windows 发布包和 Release 流程 | 普通用户能安装运行 |
| P2 | 合规、安全、开源收尾 | 仓库保持干净可信 |
| P2 | 最终验收和 PR 合并 | 项目进入可发布主线 |

## 文件职责地图

以下是后续开发会反复接触的文件，先锁定职责边界：

- `src/ivo/cli.py`：CLI 命令入口，新增命令只做参数解析和用户输出，不写复杂业务逻辑。
- `src/ivo/environment.py`：本地模型依赖、模型目录、下载渠道、许可证和 verify 命令元数据。
- `src/ivo/local_readiness.py`：profile readiness 检查，判断包、模型目录、环境变量和 engine command 是否具备。
- `src/ivo/profile_validation.py`：profile 静态结构校验。
- `src/ivo/model_smoke.py`：小型本地模型 smoke probe。
- `src/ivo/evaluation.py`：项目和批量评估报告。
- `src/ivo/adapters/base.py`：所有 adapter 的统一上下文和结果合约。
- `src/ivo/adapters/http.py`：线上 API profile 执行。
- `src/ivo/adapters/local.py`：本地命令 profile 执行。
- `src/ivo/pipeline/local_command_preview.py`：真实或 dry-run 本地命令预览主流程。
- `src/ivo/pipeline/transcribe.py`：ASR 片段和说话人映射逻辑。
- `src/ivo/pipeline/translate.py`：翻译和 style prompt 生成逻辑。
- `src/ivo/pipeline/synthesize.py`：参考音频、参考文本、TTS 输出、质量标记。
- `src/ivo/pipeline/mix_export.py`：音频叠放、背景音混合、最终 MP4 导出。
- `src/ivo/ui/main_window.py`：主窗口、用户操作入口、后台任务连接。
- `src/ivo/ui/model_settings.py`：模型和 profile 设置 UI。
- `src/ivo/ui/workers.py`：后台 worker 和 UI 线程隔离。
- `examples/local_commands/`：真实模型命令 wrapper，每个 wrapper 输出标准 JSON。
- `examples/local_command_profiles.*.json`：可运行 profile 示例。
- `examples/http_*.example.json`：线上 API profile 示例。
- `docs/evaluation/`：真实样片评估规范和每轮运行记录。
- `docs/local-model-setup.md`：模型安装、下载、许可证和 smoke 命令。
- `docs/ui-local-preview.md`：UI 真实预览使用说明。
- `docs/windows-packaging.md`：Windows 打包和发布。

## 通用执行规则

每个任务都按以下节奏执行：

1. 写或更新最小失败测试。
2. 运行目标测试，确认失败原因符合预期。
3. 实现最小改动。
4. 运行目标测试，确认通过。
5. 运行 `uv run ruff check .` 和 `uv run mypy src`。
6. 对有真实模型影响的任务，跑 20 秒真实样片或 dry-run smoke。
7. 更新对应文档和验收记录。
8. `git status --short` 确认没有真实素材或模型权重。
9. commit/push，等待 GitHub CI 通过。

通用验证命令：

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
uv run ivo doctor
uv run ivo doctor-models
uv run ivo validate-local-profiles .\examples\local_command_profiles.real_separation_asr_tts_f5_cpu_small.json --json
uv run ivo check-local-readiness .\examples\local_command_profiles.real_separation_asr_tts_f5_cpu_small.json --json
```

---

## Task 1: 当前状态文档和验收矩阵统一

**目标：** 让 README、评估文档、剩余计划和当前真实验收结果保持一致，避免后续开发者按过时路线工作。

**Files:**
- Modify: `README.md`
- Modify: `docs/evaluation/real-video-evaluation.md`
- Modify: `docs/evaluation/runs/README.md`
- Create: `docs/evaluation/acceptance-matrix.md`
- Test: `tests/test_evaluation_report.py`

- [ ] **Step 1: 写失败测试，固定评估矩阵字段**

  在 `tests/test_evaluation_report.py` 增加测试，要求评估矩阵文档包含阶段、样片、模型组合、通过条件、失败处理。

  ```python
  def test_acceptance_matrix_documents_required_fields() -> None:
      text = Path("docs/evaluation/acceptance-matrix.md").read_text(encoding="utf-8")

      for heading in (
          "## 阶段验收矩阵",
          "## 样片分层",
          "## 模型组合",
          "## 通过条件",
          "## 失败处理",
      ):
          assert heading in text
  ```

- [ ] **Step 2: 运行测试确认失败**

  ```powershell
  uv run pytest tests/test_evaluation_report.py::test_acceptance_matrix_documents_required_fields -v
  ```

  Expected: fail because `docs/evaluation/acceptance-matrix.md` does not exist or headings are missing.

- [ ] **Step 3: 创建 `docs/evaluation/acceptance-matrix.md`**

  文档必须包含：

  - 20 秒 smoke：验证命令链路是否可运行。
  - 1-3 分钟单角色/双角色：验证可看性和角色一致性。
  - 5-10 分钟多角色：验证恢复、重试、批处理。
  - 整集级别：验证长视频和性能。
  - 每个阶段的通过标准：ASR、separation、diarization、translation、TTS、mix/export、UI。

- [ ] **Step 4: 更新 README 当前状态**

  README 当前状态应写清：

  - 已跑通真实 20 秒 F5 本地预览。
  - F5-TTS 权重许可证为 CC-BY-NC，商业用途需谨慎。
  - CosyVoice 是下一条优先评估的真实 TTS 路线。
  - 真实素材和模型权重不进入 Git。

- [ ] **Step 5: 验证**

  ```powershell
  uv run pytest tests/test_evaluation_report.py -v
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 6: 提交**

  ```powershell
  git add README.md docs/evaluation/real-video-evaluation.md docs/evaluation/runs/README.md docs/evaluation/acceptance-matrix.md tests/test_evaluation_report.py
  git commit -m "docs: align remaining acceptance matrix"
  git push
  ```

---

## Task 2: 真实样片运行记录自动化

**目标：** 每次真实视频测试后自动生成运行记录，减少手工文档误差。

**Files:**
- Create: `src/ivo/evaluation_runs.py`
- Modify: `src/ivo/cli.py`
- Modify: `src/ivo/evaluation.py`
- Test: `tests/test_evaluation_report.py`

- [ ] **Step 1: 写失败测试，定义运行记录生成 API**

  ```python
  def test_render_run_markdown_includes_command_and_result(tmp_path) -> None:
      from ivo.evaluation_runs import EvaluationRunRecord, render_run_markdown

      record = EvaluationRunRecord(
          date="2026-06-05",
          title="Real F5 20s",
          source_language="ja",
          duration_seconds=20,
          profile_path="examples/local_command_profiles.real_separation_asr_tts_f5_cpu_small.json",
          command="uv run ivo local-preview sample.mp4 output --profiles profile.json",
          output_video="C:/Temp/output.ivoproj/renders/local-preview.mp4",
          status="passed",
          notes=["5 segments rendered", "CPU F5 took about 7 minutes"],
      )

      markdown = render_run_markdown(record)

      assert "# 2026-06-05 Real F5 20s" in markdown
      assert "source_language: ja" in markdown
      assert "status: passed" in markdown
      assert "uv run ivo local-preview" in markdown
      assert "5 segments rendered" in markdown
  ```

- [ ] **Step 2: 实现 `EvaluationRunRecord`**

  在 `src/ivo/evaluation_runs.py` 中实现 pydantic model：

  ```python
  class EvaluationRunRecord(BaseModel):
      date: str
      title: str
      source_language: str
      duration_seconds: int
      profile_path: str
      command: str
      output_video: str | None = None
      status: Literal["passed", "failed", "partial"]
      notes: list[str] = Field(default_factory=list)
  ```

- [ ] **Step 3: 增加 CLI 命令 `ivo evaluation write-run`**

  命令参数：

  ```text
  --title
  --source-language
  --duration-seconds
  --profile
  --command
  --output-video
  --status
  --note
  --output
  ```

  输出文件默认写到 `docs/evaluation/runs/YYYY-MM-DD-<slug>.md`。

- [ ] **Step 4: 验证**

  ```powershell
  uv run pytest tests/test_evaluation_report.py -v
  uv run ivo evaluation write-run --title "Real F5 20s" --source-language ja --duration-seconds 20 --profile .\examples\local_command_profiles.real_separation_asr_tts_f5_cpu_small.json --command "uv run ivo local-preview ..." --status passed --note "5 segments rendered" --output .\scratch\run.md
  ```

- [ ] **Step 5: 提交**

  ```powershell
  git add src/ivo/evaluation_runs.py src/ivo/cli.py src/ivo/evaluation.py tests/test_evaluation_report.py
  git commit -m "feat: add evaluation run markdown writer"
  git push
  ```

---

## Task 3: CosyVoice 真实本地 TTS 路线

**目标：** 在 F5-TTS 已跑通的基础上，补齐 CosyVoice 真实生成路线，优先评估许可证更适合开源/商业场景的模型。

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `src/ivo/environment.py`
- Modify: `examples/local_commands/cosyvoice_tts.py`
- Modify: `examples/engine_commands/cosyvoice_engine_command.example.json`
- Modify: `examples/local_command_profiles.real_tts_cosyvoice.json`
- Create: `examples/local_command_profiles.real_separation_asr_tts_cosyvoice_cpu_small.json`
- Test: `tests/examples/test_real_command_skeletons.py`
- Test: `tests/examples/test_local_command_examples.py`
- Test: `tests/test_smoke.py`

- [ ] **Step 1: 写失败测试，要求 pyproject 声明 CosyVoice extra**

  ```python
  def test_pyproject_declares_local_tts_cosyvoice_extra() -> None:
      import tomllib

      data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
      extras = data["project"]["optional-dependencies"]

      assert "local-tts-cosyvoice" in extras
      assert any("cosyvoice" in dep.lower() for dep in extras["local-tts-cosyvoice"])
  ```

  如果 CosyVoice 无法直接通过 PyPI 安装，extra 仍需包含可安装的桥接依赖，例如 `modelscope`、`soundfile`、`librosa`，同时 `environment.py` 写清手动安装路径。

- [ ] **Step 2: 写失败测试，要求 CosyVoice engine command 使用输出目录和文件名**

  ```python
  def test_cosyvoice_engine_command_uses_output_dir_and_name() -> None:
      raw = Path("examples/engine_commands/cosyvoice_engine_command.example.json").read_text(
          encoding="utf-8"
      )
      command = json.loads(raw)

      assert "{audio_out_dir}" in command
      assert "{audio_out_name}" in command
      assert "{reference_text}" in command
      assert "{text}" in command
  ```

- [ ] **Step 3: 实现 CosyVoice wrapper 合约**

  `examples/local_commands/cosyvoice_tts.py` 必须支持：

  ```text
  --text
  --speaker
  --audio-out
  --json-out
  --reference-audio
  --reference-text
  --style-prompt
  --duration-ms
  --model-dir
  --engine-command-json
  --engine-command-json-file
  --dry-run
  ```

  成功输出 JSON：

  ```json
  {
    "audio_path": "path/to/output.wav",
    "duration_ms": 2500
  }
  ```

- [ ] **Step 4: 创建 CPU 小模型完整 profile**

  新文件 `examples/local_command_profiles.real_separation_asr_tts_cosyvoice_cpu_small.json` 组合：

  - separation: `demucs-htdemucs-cpu`
  - asr: `faster-whisper-small-cpu`
  - tts: `cosyvoice-local`

  TTS 命令必须传：

  ```json
  "--reference-audio",
  "{{ reference_audio_path }}",
  "--reference-text",
  "{{ reference_text }}"
  ```

- [ ] **Step 5: 真实最小生成**

  在本机下载或配置 CosyVoice 后运行：

  ```powershell
  uv run ivo doctor-models --stage tts
  uv run python .\examples\local_commands\cosyvoice_tts.py --text "你好，我们继续测试。" --speaker speaker-1 --audio-out C:\Users\Administrator\AppData\Local\Temp\ivo_real_probe\cosyvoice_real.wav --json-out C:\Users\Administrator\AppData\Local\Temp\ivo_real_probe\cosyvoice_real.json --reference-audio C:\Users\Administrator\AppData\Local\Temp\ivo_real_probe\f5_ref_5s.wav --reference-text "参考音频文本" --duration-ms 2500 --engine-command-json-file .\examples\engine_commands\cosyvoice_engine_command.example.json
  ```

- [ ] **Step 6: 真实 20 秒 local-preview**

  ```powershell
  uv run ivo local-preview C:\Users\Administrator\AppData\Local\Temp\ivo_real_probe\jp_probe_20s.mp4 C:\Users\Administrator\AppData\Local\Temp\ivo_real_preview_cosyvoice --profiles .\examples\local_command_profiles.real_separation_asr_tts_cosyvoice_cpu_small.json --project-name JP-Real-CosyVoice-20s --source-language ja --require-readiness --no-watermark
  ```

- [ ] **Step 7: 验证**

  ```powershell
  uv run pytest tests/examples/test_real_command_skeletons.py tests/examples/test_local_command_examples.py tests/test_smoke.py -v
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 8: 提交**

  ```powershell
  git add pyproject.toml uv.lock src/ivo/environment.py examples/local_commands/cosyvoice_tts.py examples/engine_commands/cosyvoice_engine_command.example.json examples/local_command_profiles.real_tts_cosyvoice.json examples/local_command_profiles.real_separation_asr_tts_cosyvoice_cpu_small.json tests/examples/test_real_command_skeletons.py tests/examples/test_local_command_examples.py tests/test_smoke.py docs/local-model-setup.md docs/evaluation/runs
  git commit -m "feat: validate real cosyvoice tts preview"
  git push
  ```

---

## Task 4: 线上 API 全阶段真实验证

**目标：** 让用户可以使用自定义线上模型 API 完成 ASR、分离、说话人分离、翻译、TTS 任一阶段或全阶段替换。

**Files:**
- Modify: `src/ivo/adapters/http.py`
- Modify: `src/ivo/adapters/profiles.py`
- Modify: `src/ivo/cli.py`
- Modify: `examples/http_asr_profile.example.json`
- Modify: `examples/http_diarization_profile.example.json`
- Modify: `examples/http_separation_profile.example.json`
- Modify: `examples/http_translation_openai_compatible.example.json`
- Modify: `examples/http_tts_profile.example.json`
- Create: `docs/http-api-profiles.md`
- Test: `tests/adapters/test_http_adapter.py`
- Test: `tests/examples/test_http_profile_examples.py`
- Test: `tests/pipeline/test_http_asr_adapter.py`
- Test: `tests/pipeline/test_http_diarization_adapter.py`
- Test: `tests/pipeline/test_http_separation_adapter.py`
- Test: `tests/pipeline/test_http_tts_adapter.py`

- [ ] **Step 1: 写失败测试，要求 HTTP profile 支持响应错误摘要**

  ```python
  def test_http_adapter_reports_provider_error_summary(respx_mock) -> None:
      from ivo.adapters.http import HttpStageAdapter
      from ivo.adapters.profiles import ApiAdapterProfile

      profile = ApiAdapterProfile(
          id="bad-tts",
          stage="tts",
          method="POST",
          url="https://api.example.test/tts",
          headers={},
          request_template={"text": "{{ segment_text }}"},
          response_mapping={"audio_base64": "$.audio"},
          timeout_seconds=10,
      )
      respx_mock.post("https://api.example.test/tts").respond(
          500, json={"error": {"message": "quota exhausted"}}
      )

      result = HttpStageAdapter(profile).run(_adapter_context())

      assert not result.ok
      assert result.error is not None
      assert result.error.http_status == 500
      assert "quota exhausted" in result.error.message
  ```

- [ ] **Step 2: 支持 multipart 和 JSON 的统一文档**

  `docs/http-api-profiles.md` 必须包含：

  - JSON API 示例。
  - multipart 文件上传示例。
  - OpenAI-compatible 翻译示例。
  - TTS 返回 `audio_base64` 示例。
  - TTS 返回 `audio_path` 示例。
  - API key 使用 `--*-var api_key=...` 或环境变量，不写入仓库。

- [ ] **Step 3: 补齐 profile 示例的字段**

  每个 `examples/http_*.example.json` 必须包含：

  - `id`
  - `stage`
  - `method`
  - `url`
  - `headers`
  - `request_template`
  - `response_mapping`
  - `timeout_seconds`

- [ ] **Step 4: 运行本地模拟 HTTP 测试**

  使用 `respx` 或现有 HTTP 测试工具模拟线上 API，覆盖：

  - ASR segments 返回。
  - diarization speakers 返回。
  - separation base64 返回。
  - translation target_text/style_prompt 返回。
  - TTS audio_base64 返回。

- [ ] **Step 5: 使用真实或本地 HTTP 服务 smoke**

  允许用户把本地 OpenAI-compatible 服务配置为翻译 provider：

  ```powershell
  uv run ivo validate-http-profile .\examples\http_translation_openai_compatible.example.json --json
  uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_separation_asr_tts_f5_cpu_small.json --translation-profile .\examples\http_translation_openai_compatible.example.json --translation-var base_url=http://127.0.0.1:8000/v1 --translation-var api_key=local-key --project-name "HTTP Translation Probe" --source-language ja --no-watermark
  ```

- [ ] **Step 6: 验证**

  ```powershell
  uv run pytest tests/adapters/test_http_adapter.py tests/examples/test_http_profile_examples.py tests/pipeline/test_http_asr_adapter.py tests/pipeline/test_http_diarization_adapter.py tests/pipeline/test_http_separation_adapter.py tests/pipeline/test_http_tts_adapter.py -v
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 7: 提交**

  ```powershell
  git add src/ivo/adapters/http.py src/ivo/adapters/profiles.py src/ivo/cli.py examples/http_*.json docs/http-api-profiles.md tests/adapters/test_http_adapter.py tests/examples/test_http_profile_examples.py tests/pipeline/test_http_*_adapter.py
  git commit -m "feat: harden http provider profiles"
  git push
  ```

---

## Task 5: 说话人分离和角色时间线映射

**目标：** 将 pyannote 说话人分离稳定接入时间线，使多角色剧集可以绑定角色音色。

**Files:**
- Modify: `examples/local_commands/pyannote_diarization.py`
- Modify: `examples/local_command_profiles.real_diarization.json`
- Modify: `src/ivo/pipeline/transcribe.py`
- Modify: `src/ivo/pipeline/local_command_preview.py`
- Modify: `src/ivo/core/timeline.py`
- Test: `tests/pipeline/test_transcribe.py`
- Test: `tests/pipeline/test_local_command_preview.py`
- Test: `tests/examples/test_local_command_examples.py`

- [ ] **Step 1: 写失败测试，要求重叠最大者成为 speaker**

  ```python
  def test_diarization_assigns_speaker_by_largest_overlap() -> None:
      from ivo.pipeline.transcribe import TranscriptionSegment, DiarizationSegment, merge_speakers

      asr_segments = [
          TranscriptionSegment(
              id="seg-001",
              start_ms=1000,
              end_ms=3000,
              source_language="ja",
              source_text="こんにちは",
              speaker_id="unknown",
          )
      ]
      diarization = [
          DiarizationSegment(start_ms=900, end_ms=1500, speaker_id="speaker-1"),
          DiarizationSegment(start_ms=1500, end_ms=3200, speaker_id="speaker-2"),
      ]

      merged = merge_speakers(asr_segments, diarization)

      assert merged[0].speaker_id == "speaker-2"
  ```

- [ ] **Step 2: 实现 diarization wrapper 输出合约**

  `pyannote_diarization.py` 输出：

  ```json
  {
    "segments": [
      {
        "start_ms": 900,
        "end_ms": 1500,
        "speaker_id": "speaker-1"
      }
    ]
  }
  ```

- [ ] **Step 3: 加入质量标记**

  当没有任何 diarization 段覆盖 ASR 片段时：

  - 保留原 `speaker_id` 或设为 `unknown`。
  - 给时间线片段添加 `speaker_unmatched`。

  当多个 speaker 覆盖比例接近时：

  - 选择覆盖最长者。
  - 添加 `speaker_ambiguous`。

- [ ] **Step 4: pyannote readiness**

  `doctor-models --stage diarization` 必须显示：

  - `pyannote.audio` 是否安装。
  - `HF_TOKEN` 是否存在。
  - `models/diarization/pyannote-community-1` 是否存在。
  - 模型条款需要用户在 Hugging Face 接受。

- [ ] **Step 5: 真实样片验证**

  使用多说话人授权样片：

  ```powershell
  $env:HF_TOKEN="your-token"
  uv run ivo local-preview .\sample_media\multi_speaker_1min.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_diarization.json --project-name "Diarization Probe" --source-language ja --require-readiness --no-watermark
  ```

- [ ] **Step 6: 验证**

  ```powershell
  uv run pytest tests/pipeline/test_transcribe.py tests/pipeline/test_local_command_preview.py tests/examples/test_local_command_examples.py -v
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 7: 提交**

  ```powershell
  git add examples/local_commands/pyannote_diarization.py examples/local_command_profiles.real_diarization.json src/ivo/pipeline/transcribe.py src/ivo/pipeline/local_command_preview.py src/ivo/core/timeline.py tests/pipeline/test_transcribe.py tests/pipeline/test_local_command_preview.py tests/examples/test_local_command_examples.py docs/evaluation/runs
  git commit -m "feat: map diarization speakers to timeline"
  git push
  ```

---

## Task 6: 角色音色资料和参考片段管理

**目标：** 让每个角色拥有可查看、可编辑、可替换的参考音频和参考文本，提升多角色一致性。

**Files:**
- Modify: `src/ivo/core/timeline.py`
- Modify: `src/ivo/pipeline/synthesize.py`
- Modify: `src/ivo/ui/timeline_editor.py`
- Modify: `src/ivo/ui/main_window.py`
- Create: `src/ivo/core/speakers.py`
- Test: `tests/core/test_timeline.py`
- Test: `tests/pipeline/test_synthesize.py`
- Test: `tests/ui/test_timeline_editor_actions.py`

- [ ] **Step 1: 写失败测试，定义 SpeakerProfile 存取**

  ```python
  def test_speaker_profile_stores_reference_segments(tmp_path) -> None:
      from ivo.core.project import DubbingProject
      from ivo.core.speakers import SpeakerProfile

      project = DubbingProject.create(
          tmp_path / "speakers.ivoproj",
          name="Speakers",
          source_language="ja",
          target_language="zh",
      )

      project.speakers.upsert(
          SpeakerProfile(
              id="speaker-1",
              display_name="角色 A",
              reference_segment_ids=["seg-001"],
              preferred_tts_profile_id="f5-tts-local",
          )
      )

      loaded = project.speakers.get("speaker-1")

      assert loaded is not None
      assert loaded.display_name == "角色 A"
      assert loaded.reference_segment_ids == ["seg-001"]
  ```

- [ ] **Step 2: 新增 `SpeakerProfile`**

  `src/ivo/core/speakers.py` 中定义：

  ```python
  class SpeakerProfile(BaseModel):
      id: str
      display_name: str
      reference_segment_ids: list[str] = Field(default_factory=list)
      preferred_tts_profile_id: str | None = None
      notes: str = ""
  ```

- [ ] **Step 3: 参考片段选择策略**

  `synthesize.py` 中 `extract_reference_audio` 改为：

  1. 优先使用该 speaker profile 中 `reference_segment_ids` 的第一个有效片段。
  2. 其次使用同 speaker 已 `approved` 的片段。
  3. 再使用当前片段。
  4. 无源音频时返回 `None` 并保留 `missing_reference_audio`。

- [ ] **Step 4: UI 支持角色参考片段**

  在时间线右键菜单或按钮中增加：

  - “设为该角色参考片段”
  - “清除该角色参考片段”
  - “重命名角色”

  UI 更新后，时间线中的 speaker 显示应使用 `display_name`。

- [ ] **Step 5: 验证**

  ```powershell
  uv run pytest tests/core/test_timeline.py tests/pipeline/test_synthesize.py tests/ui/test_timeline_editor_actions.py -v
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 6: 提交**

  ```powershell
  git add src/ivo/core/speakers.py src/ivo/core/timeline.py src/ivo/pipeline/synthesize.py src/ivo/ui/timeline_editor.py src/ivo/ui/main_window.py tests/core/test_timeline.py tests/pipeline/test_synthesize.py tests/ui/test_timeline_editor_actions.py
  git commit -m "feat: add speaker voice reference profiles"
  git push
  ```

---

## Task 7: 翻译质量、术语表和语气控制

**目标：** 面向美剧、日剧、韩剧对白，让翻译不仅正确，还适合配音、时长和角色语气。

**Files:**
- Modify: `src/ivo/pipeline/translate.py`
- Modify: `src/ivo/core/settings.py`
- Modify: `src/ivo/ui/project_wizard.py`
- Modify: `examples/http_translation_openai_compatible.example.json`
- Create: `docs/translation-style-guide.md`
- Test: `tests/pipeline/test_translate.py`
- Test: `tests/core/test_settings.py`
- Test: `tests/ui/test_project_wizard_file_selection.py`

- [ ] **Step 1: 写失败测试，要求术语表影响 prompt**

  ```python
  def test_translation_prompt_includes_glossary_terms() -> None:
      from ivo.pipeline.translate import build_translation_prompt

      prompt = build_translation_prompt(
          source_language="ja",
          target_language="zh",
          source_text="先輩、お願いします",
          duration_ms=1800,
          speaker_id="speaker-1",
          glossary={"先輩": "前辈"},
          style_notes="日剧口吻，自然，不要书面腔。",
      )

      assert "先輩 -> 前辈" in prompt
      assert "日剧口吻" in prompt
      assert "1800ms" in prompt
  ```

- [ ] **Step 2: 增加项目级翻译配置**

  `core/settings.py` 增加：

  - `translation_style_notes: str`
  - `glossary: dict[str, str]`
  - `preserve_fillers: bool`
  - `max_length_ratio: float`

- [ ] **Step 3: 固定翻译输出 schema**

  翻译 provider 应返回：

  ```json
  {
    "target_text": "前辈，拜托了。",
    "emotion": "pleading",
    "style_prompt": "带一点请求感，语速自然，保留短暂停顿"
  }
  ```

  如果 provider 只返回字符串，流水线应兼容并只更新 `target_text`。

- [ ] **Step 4: 项目向导增加风格设置**

  在 `project_wizard.py` 添加：

  - 剧集类型：美剧、日剧、韩剧、其他。
  - 风格备注多行输入。
  - 术语表文件选择，支持 JSON。

- [ ] **Step 5: 文档**

  `docs/translation-style-guide.md` 写清：

  - 美剧对白：口语、节奏快、避免翻译腔。
  - 日剧对白：敬语、称呼、停顿和语气词。
  - 韩剧对白：称谓、情绪递进、短句自然。
  - 术语表格式。
  - style prompt 如何传给 TTS。

- [ ] **Step 6: 验证**

  ```powershell
  uv run pytest tests/pipeline/test_translate.py tests/core/test_settings.py tests/ui/test_project_wizard_file_selection.py -v
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 7: 提交**

  ```powershell
  git add src/ivo/pipeline/translate.py src/ivo/core/settings.py src/ivo/ui/project_wizard.py examples/http_translation_openai_compatible.example.json docs/translation-style-guide.md tests/pipeline/test_translate.py tests/core/test_settings.py tests/ui/test_project_wizard_file_selection.py
  git commit -m "feat: add translation style and glossary controls"
  git push
  ```

---

## Task 8: TTS 时长对齐、重试和音频质量标记

**目标：** 减少 TTS 生成过长、过短、全静音、音量异常对最终观看体验的影响。

**Files:**
- Modify: `src/ivo/pipeline/synthesize.py`
- Modify: `src/ivo/evaluation.py`
- Modify: `src/ivo/ui/timeline_editor.py`
- Test: `tests/pipeline/test_synthesize.py`
- Test: `tests/test_evaluation_report.py`
- Test: `tests/ui/test_timeline_editor_editing.py`

- [ ] **Step 1: 写失败测试，定义音频质量标记**

  ```python
  def test_synthesis_marks_short_audio(tmp_path) -> None:
      from ivo.pipeline.synthesize import _merge_synthesis_quality_flags

      flags = _merge_synthesis_quality_flags(
          [],
          duration_flag="duration_too_short",
          reference_missing=False,
          silent_audio=False,
      )

      assert "duration_too_short" in flags
  ```

- [ ] **Step 2: 拆分时长标记**

  当前 `duration_mismatch` 拆成：

  - `duration_ok`
  - `duration_too_short`
  - `duration_too_long`

  规则：

  - 生成音频与目标时长差值小于等于 `tolerance_ms`：`duration_ok`
  - 生成音频短于目标超过容差：`duration_too_short`
  - 生成音频长于目标超过容差：`duration_too_long`

- [ ] **Step 3: 增加自动重试策略**

  对支持 style prompt 的 TTS：

  - 过长：追加 `语速稍快，表达更简短`
  - 过短：追加 `语速稍慢，停顿自然`
  - 最多重试 1 次，避免 CPU 上无限耗时。

  重试后的片段质量标记添加：

  - `tts_retried`
  - 如果仍失败，保留最终 duration flag。

- [ ] **Step 4: 评估报告统计**

  `evaluate-project` 增加统计：

  - `duration_too_short`
  - `duration_too_long`
  - `tts_retried`
  - `silent_audio`

- [ ] **Step 5: UI 显示**

  时间线质量标记列显示中文摘要：

  - `duration_too_short` -> “配音偏短”
  - `duration_too_long` -> “配音偏长”
  - `tts_retried` -> “已自动重试”

- [ ] **Step 6: 验证**

  ```powershell
  uv run pytest tests/pipeline/test_synthesize.py tests/test_evaluation_report.py tests/ui/test_timeline_editor_editing.py -v
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 7: 提交**

  ```powershell
  git add src/ivo/pipeline/synthesize.py src/ivo/evaluation.py src/ivo/ui/timeline_editor.py tests/pipeline/test_synthesize.py tests/test_evaluation_report.py tests/ui/test_timeline_editor_editing.py
  git commit -m "feat: add tts duration retry quality flags"
  git push
  ```

---

## Task 9: UI 模型配置、profile 选择和 readiness 面板

**目标：** 用户不靠命令行也能选择本地/线上 profile、检查依赖、看懂缺什么。

**Files:**
- Modify: `src/ivo/ui/model_settings.py`
- Modify: `src/ivo/ui/main_window.py`
- Modify: `src/ivo/ui/workers.py`
- Modify: `src/ivo/local_readiness.py`
- Modify: `docs/ui-local-preview.md`
- Test: `tests/ui/test_main_window_local_preview.py`
- Test: `tests/ui/test_main_window_error_handling.py`
- Test: `tests/test_local_readiness.py`

- [ ] **Step 1: 写失败 UI 测试，要求显示 readiness 缺失项**

  ```python
  def test_model_settings_shows_missing_tts_dependency(qtbot, tmp_path) -> None:
      from ivo.ui.model_settings import ModelSettingsPanel

      panel = ModelSettingsPanel()
      qtbot.addWidget(panel)

      panel.show_readiness_results(
          [
              {
                  "stage": "tts",
                  "provider": "CosyVoice",
                  "status": "missing",
                  "message": "cosyvoice package is missing",
              }
          ]
      )

      assert "CosyVoice" in panel.readiness_summary_text()
      assert "missing" in panel.readiness_summary_text()
  ```

- [ ] **Step 2: Profile 选择 UI**

  `model_settings.py` 增加：

  - 本地 profile 文件选择。
  - HTTP profile 文件选择。
  - `check-local-readiness` 按钮。
  - `validate-http-profile` 按钮。
  - JSON 结果以表格显示 stage/provider/status/message。

- [ ] **Step 3: 主窗口运行时使用 UI profile**

  `main_window.py` local preview 启动时：

  - 读取用户选择的 local profile。
  - 可选读取 stage override 的 HTTP profile。
  - 将 profile 路径保存到项目设置。

- [ ] **Step 4: 后台 worker**

  `workers.py` 增加 readiness worker：

  - 输入 profile 路径和 models dir。
  - 调用 `local_readiness.check_profiles_readiness`。
  - 把结构化结果发回 UI，不阻塞界面。

- [ ] **Step 5: 文档**

  `docs/ui-local-preview.md` 增加：

  - 如何选择 `real_separation_asr_tts_f5_cpu_small`。
  - 如何检查缺包。
  - 如何把线上翻译 profile 作为 override。
  - 如何处理 `HF_TOKEN`、模型目录和 engine command 文件缺失。

- [ ] **Step 6: 验证**

  ```powershell
  uv run pytest tests/ui/test_main_window_local_preview.py tests/ui/test_main_window_error_handling.py tests/test_local_readiness.py -v
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 7: UI 冒烟**

  ```powershell
  uv run python -m ivo.app
  ```

  手工确认：

  - 模型设置页能打开。
  - profile 路径能选择。
  - readiness 结果能显示。
  - UI 没有卡死。

- [ ] **Step 8: 提交**

  ```powershell
  git add src/ivo/ui/model_settings.py src/ivo/ui/main_window.py src/ivo/ui/workers.py src/ivo/local_readiness.py docs/ui-local-preview.md tests/ui/test_main_window_local_preview.py tests/ui/test_main_window_error_handling.py tests/test_local_readiness.py
  git commit -m "feat: add ui model readiness panel"
  git push
  ```

---

## Task 10: UI 运行日志和错误定位

**目标：** 真实模型失败时，用户能看到阶段、provider、命令、退出码、stderr 摘要和下一步建议。

**Files:**
- Modify: `src/ivo/adapters/base.py`
- Modify: `src/ivo/adapters/local.py`
- Modify: `src/ivo/ui/main_window.py`
- Modify: `src/ivo/ui/workers.py`
- Create: `src/ivo/ui/run_log.py`
- Test: `tests/adapters/test_local_command_adapter.py`
- Test: `tests/ui/test_main_window_error_handling.py`

- [ ] **Step 1: 写失败测试，要求 local command 错误包含 stderr 摘要**

  ```python
  def test_local_command_error_includes_stderr_summary(tmp_path) -> None:
      from ivo.adapters.local import LocalCommandAdapter, LocalCommandProfile

      profile = LocalCommandProfile(
          id="bad-command",
          stage="tts",
          command=["python", "-c", "import sys; sys.stderr.write('model missing'); sys.exit(1)"],
          output_json_path=str(tmp_path / "missing.json"),
      )

      result = LocalCommandAdapter(profile).run(_adapter_context(tmp_path))

      assert not result.ok
      assert result.error is not None
      assert "model missing" in result.error.message
  ```

- [ ] **Step 2: 标准化错误 payload**

  `AdapterError` 增加：

  - `command: list[str] | None`
  - `exit_code: int | None`
  - `stderr_summary: str | None`
  - `output_json_path: str | None`

- [ ] **Step 3: UI Run Log Panel**

  `src/ivo/ui/run_log.py` 提供：

  - `append_stage_message(stage, message)`
  - `append_adapter_error(error)`
  - `plain_text()`
  - “复制日志”按钮。

- [ ] **Step 4: 主窗口接入**

  `main_window.py` 将 worker 进度、adapter error、最终输出路径写入日志面板。

- [ ] **Step 5: 验证**

  ```powershell
  uv run pytest tests/adapters/test_local_command_adapter.py tests/ui/test_main_window_error_handling.py -v
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 6: 提交**

  ```powershell
  git add src/ivo/adapters/base.py src/ivo/adapters/local.py src/ivo/ui/main_window.py src/ivo/ui/workers.py src/ivo/ui/run_log.py tests/adapters/test_local_command_adapter.py tests/ui/test_main_window_error_handling.py
  git commit -m "feat: surface model run errors in ui logs"
  git push
  ```

---

## Task 11: 质量面板和逐句审核工作流

**目标：** 用户能按质量问题过滤片段、修订译文或 style prompt、重生成单句、再导出。

**Files:**
- Modify: `src/ivo/ui/timeline_editor.py`
- Modify: `src/ivo/ui/main_window.py`
- Modify: `src/ivo/evaluation.py`
- Test: `tests/ui/test_timeline_editor_actions.py`
- Test: `tests/ui/test_main_window_regenerate_segment.py`
- Test: `tests/test_evaluation_report.py`

- [ ] **Step 1: 写失败测试，按质量标记过滤片段**

  ```python
  def test_timeline_editor_filters_duration_flags(qtbot) -> None:
      from ivo.ui.timeline_editor import TimelineEditor

      editor = TimelineEditor()
      qtbot.addWidget(editor)
      editor.set_segments(
          [
              _segment("seg-001", quality_flags=["duration_too_long"]),
              _segment("seg-002", quality_flags=["duration_ok"]),
          ]
      )

      editor.set_quality_filter("duration_too_long")

      assert editor.visible_segment_ids() == ["seg-001"]
  ```

- [ ] **Step 2: UI 增加过滤器**

  时间线顶部增加：

  - 全部
  - 失败
  - 配音偏长
  - 配音偏短
  - 静音
  - 缺参考音频
  - 说话人不确定

- [ ] **Step 3: 逐句审核状态**

  每个片段可切换：

  - `needs_review`
  - `approved`
  - `rendered`

  当用户编辑 `target_text`、`speaker_id`、`style_prompt` 后，状态回到 `needs_review`，并清理旧的 rendered 音频引用。

- [ ] **Step 4: 评估摘要**

  UI 显示：

  - 总片段数。
  - 已审核数量。
  - 已生成数量。
  - 质量标记数量。

- [ ] **Step 5: 验证**

  ```powershell
  uv run pytest tests/ui/test_timeline_editor_actions.py tests/ui/test_main_window_regenerate_segment.py tests/test_evaluation_report.py -v
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 6: 提交**

  ```powershell
  git add src/ivo/ui/timeline_editor.py src/ivo/ui/main_window.py src/ivo/evaluation.py tests/ui/test_timeline_editor_actions.py tests/ui/test_main_window_regenerate_segment.py tests/test_evaluation_report.py
  git commit -m "feat: add timeline quality review workflow"
  git push
  ```

---

## Task 12: 长视频恢复、批处理和失败片段重跑

**目标：** 将当前短片段可跑通能力扩展到 1-3 分钟、5-10 分钟和多集批处理。

**Files:**
- Modify: `src/ivo/pipeline/local_command_preview.py`
- Modify: `src/ivo/core/jobs.py`
- Modify: `src/ivo/cli.py`
- Modify: `src/ivo/evaluation.py`
- Test: `tests/pipeline/test_local_command_preview.py`
- Test: `tests/core/test_project.py`
- Test: `tests/test_evaluation_report.py`

- [ ] **Step 1: 写失败测试，失败 TTS 只重跑失败片段**

  ```python
  def test_resume_failed_tts_keeps_rendered_segments(tmp_path) -> None:
      # Arrange a project with seg-001 rendered wav present and seg-002 failed.
      # Run local preview with --resume-existing.
      # Assert the TTS adapter is called only for seg-002.
  ```

  测试必须断言：

  - `seg-001.wav` 未被覆盖。
  - `seg-002.wav` 被生成。
  - timeline 中两个片段最终都是 `rendered`。

- [ ] **Step 2: 阶段产物完整性检查**

  `--resume-existing` 复用阶段前必须检查：

  - import：`assets/source_video.mp4` 存在。
  - audio_extract：`assets/extracted_audio.wav` 存在。
  - separation：`work/vocals.wav` 和 `work/background.wav` 存在。
  - asr：timeline 中有片段。
  - tts：每个 rendered 片段的 wav 存在。
  - export：`renders/local-preview.mp4` 存在。

- [ ] **Step 3: batch 报告增强**

  `batch-local-preview --report` 输出每个视频：

  ```json
  {
    "source_video": "episode01.mp4",
    "project_path": "Episode01.ivoproj",
    "status": "passed",
    "failed_stage": null,
    "final_video": "renders/local-preview.mp4",
    "duration_seconds": 1234
  }
  ```

- [ ] **Step 4: 真实 1-3 分钟样片验证**

  从用户授权视频截取 1-3 分钟到临时目录，不提交。

  ```powershell
  ffmpeg -y -i "F:\GZYproject\Intelligent-Voice-Over\测试视频\如果中日开战日本会变成什么样？日本节目展开讨论 (高清 720P, AVC, 极高音质, WEB).mp4" -t 00:01:30 C:\Users\Administrator\AppData\Local\Temp\ivo_real_probe\jp_probe_90s.mp4
  uv run ivo local-preview C:\Users\Administrator\AppData\Local\Temp\ivo_real_probe\jp_probe_90s.mp4 C:\Users\Administrator\AppData\Local\Temp\ivo_real_preview_90s --profiles .\examples\local_command_profiles.real_separation_asr_tts_f5_cpu_small.json --project-name JP-Real-F5-90s --source-language ja --require-readiness --resume-existing --no-watermark
  ```

- [ ] **Step 5: 验证**

  ```powershell
  uv run pytest tests/pipeline/test_local_command_preview.py tests/core/test_project.py tests/test_evaluation_report.py -v
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 6: 提交**

  ```powershell
  git add src/ivo/pipeline/local_command_preview.py src/ivo/core/jobs.py src/ivo/cli.py src/ivo/evaluation.py tests/pipeline/test_local_command_preview.py tests/core/test_project.py tests/test_evaluation_report.py docs/evaluation/runs
  git commit -m "feat: harden long preview resume and batch reports"
  git push
  ```

---

## Task 13: 本地模型下载脚本和安全安装体验

**目标：** 用户能生成安装脚本，但脚本明确提示许可证和 token，不自动提交模型或秘密。

**Files:**
- Modify: `src/ivo/model_setup.py`
- Modify: `src/ivo/environment.py`
- Modify: `docs/local-model-setup.md`
- Create: `scripts/setup-local-models.example.ps1`
- Test: `tests/test_model_setup_script.py`

- [ ] **Step 1: 写失败测试，脚本必须包含许可证确认注释**

  ```python
  def test_setup_script_mentions_license_and_gitignore(tmp_path) -> None:
      from ivo.model_setup import write_setup_script

      output = tmp_path / "setup.ps1"
      write_setup_script(output, models_dir=tmp_path / "models", stage=None)

      text = output.read_text(encoding="utf-8")
      assert "确认模型许可证" in text
      assert "不要提交 models/" in text
      assert "huggingface-cli login" in text
  ```

- [ ] **Step 2: 生成示例脚本**

  `scripts/setup-local-models.example.ps1` 只提交示例，不提交真实下载结果。

  脚本包含：

  - `uv sync --extra local-separation`
  - `uv sync --extra local-tts-f5`
  - Hugging Face login 提示。
  - faster-whisper 下载命令。
  - CosyVoice 下载命令。
  - F5-TTS 下载命令。
  - Qwen 下载命令。

- [ ] **Step 3: doctor 输出加入脚本提示**

  `ivo doctor-models` 末尾提示：

  ```text
  Run `uv run ivo model write-setup-script --models-dir .\models --output .\scripts\setup-local-models.ps1` to generate a local setup script.
  ```

- [ ] **Step 4: 验证**

  ```powershell
  uv run pytest tests/test_model_setup_script.py -v
  uv run ivo model write-setup-script --models-dir .\models --output .\scratch\setup-local-models.ps1
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 5: 提交**

  ```powershell
  git add src/ivo/model_setup.py src/ivo/environment.py docs/local-model-setup.md scripts/setup-local-models.example.ps1 tests/test_model_setup_script.py
  git commit -m "feat: add safe local model setup script"
  git push
  ```

---

## Task 14: GPU 和性能 profile

**目标：** 在 CPU 小模型验证之外，提供 GPU 高质量和快速预览 profile，便于真实剧集使用。

**Files:**
- Create: `examples/local_command_profiles.real_gpu_quality.json`
- Create: `examples/local_command_profiles.real_gpu_fast_preview.json`
- Modify: `docs/local-model-command-profiles.md`
- Modify: `src/ivo/local_readiness.py`
- Test: `tests/examples/test_local_command_examples.py`
- Test: `tests/test_local_readiness.py`

- [ ] **Step 1: 写失败测试，要求 GPU profile 存在**

  ```python
  def test_real_gpu_quality_profile_uses_gpu_models() -> None:
      profile = LocalCommandPipelineProfiles.model_validate(
          json.loads(Path("examples/local_command_profiles.real_gpu_quality.json").read_text(encoding="utf-8"))
      )

      assert "cuda" in profile.separation.command
      assert "cuda" in profile.asr.command
      assert profile.tts.id in {"f5-tts-local", "cosyvoice-local"}
  ```

- [ ] **Step 2: 高质量 profile**

  `real_gpu_quality.json` 推荐：

  - Demucs `htdemucs` 或 `htdemucs_ft`，`--device cuda`。
  - faster-whisper `Systran/faster-whisper-large-v3`，`--device cuda`，`--compute-type float16`。
  - TTS 使用 CosyVoice 或 F5-TTS GPU engine command。

- [ ] **Step 3: 快速预览 profile**

  `real_gpu_fast_preview.json` 推荐：

  - Demucs CPU 或较轻设置。
  - faster-whisper `small` 或 distil/turbo。
  - TTS 可使用快速模型或 dry-run 占位，明确标注不代表最终质量。

- [ ] **Step 4: readiness GPU 提示**

  如果 profile 中包含 `cuda`，readiness 检查应提示：

  - 当前是否检测到 NVIDIA 工具。
  - 如果未检测到，提示改用 CPU small profile。

- [ ] **Step 5: 验证**

  ```powershell
  uv run pytest tests/examples/test_local_command_examples.py tests/test_local_readiness.py -v
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 6: 提交**

  ```powershell
  git add examples/local_command_profiles.real_gpu_quality.json examples/local_command_profiles.real_gpu_fast_preview.json docs/local-model-command-profiles.md src/ivo/local_readiness.py tests/examples/test_local_command_examples.py tests/test_local_readiness.py
  git commit -m "feat: add gpu local model profiles"
  git push
  ```

---

## Task 15: Windows 打包和本地 Release 验证

**目标：** 生成可分发 Windows 包，并验证普通用户能启动 UI、跑 mock preview、检查模型环境。

**Files:**
- Modify: `docs/windows-packaging.md`
- Modify: `.github/workflows/ci.yml`
- Modify: `pyproject.toml`
- Create: `scripts/package-windows.ps1`
- Test: `tests/test_windows_packaging.py`

- [ ] **Step 1: 写失败测试，要求打包脚本存在并不包含模型权重**

  ```python
  def test_windows_package_script_excludes_models_and_media() -> None:
      text = Path("scripts/package-windows.ps1").read_text(encoding="utf-8")

      assert "models" in text
      assert "测试视频" in text
      assert "*.mp4" in text
      assert "*.wav" in text
      assert "pyinstaller" in text.lower()
  ```

- [ ] **Step 2: 打包脚本**

  `scripts/package-windows.ps1` 执行：

  ```powershell
  uv sync
  uv run pytest
  uv run ruff check .
  uv run mypy src
  uv run pyinstaller --name IntelligentVoiceOver --windowed --onefile src\ivo\app.py
  ```

  脚本必须在注释中写明排除：

  - `models/`
  - `测试视频/`
  - `sample_media/`
  - `scratch/`
  - `*.mp4`
  - `*.wav`
  - `.env`

- [ ] **Step 3: CI package dry-run**

  GitHub Actions 继续保留 package dry-run，但不下载真实模型。

- [ ] **Step 4: 本地安装包冒烟**

  在本机运行：

  ```powershell
  .\scripts\package-windows.ps1
  .\dist\IntelligentVoiceOver.exe
  ```

  手工确认：

  - UI 能启动。
  - `ivo doctor` 等价信息能在 UI 模型设置中看到。
  - mock preview 能导出。

- [ ] **Step 5: 验证**

  ```powershell
  uv run pytest tests/test_windows_packaging.py -v
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 6: 提交**

  ```powershell
  git add docs/windows-packaging.md .github/workflows/ci.yml pyproject.toml scripts/package-windows.ps1 tests/test_windows_packaging.py
  git commit -m "chore: add windows packaging script"
  git push
  ```

---

## Task 16: 开源合规、安全和仓库卫生

**目标：** 确保仓库公开后持续安全、可贡献、无泄密、无未授权素材。

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `SECURITY.md`
- Create: `docs/compliance-and-licenses.md`
- Test: `tests/test_smoke.py`

- [ ] **Step 1: 写失败测试，检查敏感目录忽略规则**

  ```python
  def test_gitignore_excludes_real_media_models_and_secrets() -> None:
      text = Path(".gitignore").read_text(encoding="utf-8")

      for pattern in ("models/", "测试视频/", "*.mp4", "*.wav", ".env", "scratch/"):
          assert pattern in text
  ```

- [ ] **Step 2: 合规文档**

  `docs/compliance-and-licenses.md` 必须写清：

  - 项目代码采用 PolyForm Noncommercial License 1.0.0，商业使用需另行授权。
  - 第三方模型许可证各自独立。
  - F5-TTS 权重 CC-BY-NC。
  - CosyVoice 使用前重新确认模型卡。
  - pyannote 需要接受 Hugging Face 条款。
  - 用户必须确认拥有视频处理权利。
  - 导出 AI 配音元数据和可选可见水印。

- [ ] **Step 3: README 贡献入口**

  README 增加：

  - 如何提交 issue。
  - 如何贡献 profile。
  - 不接受模型权重、真实影视片段、API key 的说明。

- [ ] **Step 4: 验证**

  ```powershell
  uv run pytest tests/test_smoke.py -v
  uv run ruff check .
  uv run mypy src
  git status --short
  ```

  `git status --short` 不能出现 `测试视频/`、`models/`、真实 `.mp4`、真实 `.wav`。

- [ ] **Step 5: 提交**

  ```powershell
  git add .gitignore README.md CONTRIBUTING.md SECURITY.md docs/compliance-and-licenses.md tests/test_smoke.py
  git commit -m "docs: strengthen open source compliance guidance"
  git push
  ```

---

## Task 17: 最终端到端验收

**目标：** 在合并主分支前，用真实样片、mock 样片、UI 和 CI 完成最终验收。

**Files:**
- Modify: `docs/evaluation/acceptance-matrix.md`
- Create: `docs/evaluation/runs/2026-06-final-acceptance.md`
- Modify: `README.md`

- [ ] **Step 1: 本地全量质量检查**

  ```powershell
  uv run pytest
  uv run ruff check .
  uv run mypy src
  uv run ivo doctor
  uv run ivo doctor-models
  ```

  Expected:

  - pytest 全部通过。
  - ruff 通过。
  - mypy 无错误。
  - doctor 能检测 FFmpeg。
  - doctor-models 能清晰区分 installed/missing。

- [ ] **Step 2: mock 端到端**

  ```powershell
  uv run python .\scripts\create_sample_media.py --output-dir .\sample_media
  uv run ivo mock-preview .\sample_media\sample.mp4 .\scratch\mock-final --project-name "Mock Final" --source-language en --no-watermark
  uv run ivo evaluate-project .\scratch\mock-final\Mock-Final.ivoproj --json
  ```

  Expected:

  - 项目目录创建成功。
  - `renders/preview.mp4` 或 `renders/local-preview.mp4` 存在。
  - evaluation JSON 中没有 failed jobs。

- [ ] **Step 3: 真实 20 秒 F5 本地链路**

  ```powershell
  uv run ivo local-preview C:\Users\Administrator\AppData\Local\Temp\ivo_real_probe\jp_probe_20s.mp4 C:\Users\Administrator\AppData\Local\Temp\ivo_final_f5_20s --profiles .\examples\local_command_profiles.real_separation_asr_tts_f5_cpu_small.json --project-name JP-Final-F5-20s --source-language ja --require-readiness --resume-existing --no-watermark
  uv run ivo evaluate-project C:\Users\Administrator\AppData\Local\Temp\ivo_final_f5_20s\JP-Final-F5-20s.ivoproj --json
  ```

  Expected:

  - final video exists。
  - import、audio_extract、separation、asr、translation、tts、export 均 completed。
  - 所有片段状态为 `rendered` 或可解释的质量标记。

- [ ] **Step 4: 真实 1-3 分钟样片**

  使用 Task 12 的 90 秒样片或新的授权样片。

  Expected:

  - 可以完成或可恢复。
  - 如果失败，失败阶段、provider、stderr 摘要清晰可见。
  - `--resume-existing` 能复用已完成阶段。

- [ ] **Step 5: UI 冒烟**

  ```powershell
  uv run python -m ivo.app
  ```

  手工确认：

  - 新建项目。
  - 选择 profile。
  - readiness 检查。
  - 运行 mock 或 local preview。
  - 查看时间线。
  - 修改一句译文。
  - 重生成一句。
  - 导出。

- [ ] **Step 6: GitHub CI**

  ```powershell
  git push
  gh run list --repo gzyasd/intelligent-voice-over --limit 5
  gh run watch <latest-run-id> --repo gzyasd/intelligent-voice-over --exit-status
  ```

  Expected: CI success。

- [ ] **Step 7: 最终文档**

  `docs/evaluation/runs/2026-06-final-acceptance.md` 记录：

  - 本地命令。
  - 模型组合。
  - 输出路径。
  - 结果。
  - 已知限制。
  - 下一版建议。

- [ ] **Step 8: 最终提交**

  ```powershell
  git add README.md docs/evaluation/acceptance-matrix.md docs/evaluation/runs/2026-06-final-acceptance.md
  git commit -m "docs: record final acceptance results"
  git push
  ```

---

## 最终验收标准

P0 可发布预览版必须满足：

- [ ] 用户可通过 README 安装依赖并运行 `uv run ivo doctor`。
- [ ] 用户可通过 CLI 或 UI 运行 mock preview。
- [ ] 用户可通过 CLI 运行至少一个真实本地模型 20 秒视频链路。
- [ ] 项目支持本地模型和线上 HTTP API 两种方式。
- [ ] 每个真实模型 profile 可被 `validate-local-profiles` 和 `check-local-readiness` 检查。
- [ ] 失败时能指出 stage、provider、命令、退出码或 HTTP 状态。
- [ ] 时间线可编辑译文、speaker、style prompt，并可单句重生成。
- [ ] 最终导出写入 AI 配音元数据，并提供可选可见水印。
- [ ] 真实素材、模型权重、API key、token 不进入仓库。
- [ ] GitHub CI 通过。

P1 可长期使用版必须满足：

- [ ] 1-3 分钟真实样片稳定跑通。
- [ ] 多说话人样片能进行 speaker 映射和角色音色绑定。
- [ ] 用户能在 UI 中选择 profile、检查 readiness、查看运行日志。
- [ ] 质量面板能过滤失败、时长问题、静音、缺参考音频、speaker 不确定。
- [ ] `--resume-existing` 能恢复中断项目。
- [ ] batch-local-preview 能处理目录中的多集视频并输出报告。

P2 发布版必须满足：

- [ ] Windows 打包脚本通过。
- [ ] Release 文档说明不包含模型权重和影视素材。
- [ ] 合规文档说明第三方模型许可证和用户素材授权责任。
- [ ] 最终验收文档记录 mock、真实 20 秒、1-3 分钟和 UI 冒烟结果。

## 已知限制和下一版方向

本计划完成后，项目仍不包含以下能力：

- 视频口型重定向和画面级 lip-sync。
- 云端任务队列和多人协作。
- 自动版权判断。
- 商业可用模型许可证担保。
- 角色级长期记忆和跨集统一音色训练。

下一版可以考虑：

- 对接更高质量的商用 TTS API。
- 增加字幕文件导入和导出。
- 增加口型同步服务 adapter。
- 增加跨集角色 voice book。
- 增加 Web UI 或轻量服务端队列。

## 自检

- Spec 覆盖：本计划覆盖本地模型、线上 API、UI、质量评估、长视频、发布、合规和最终验收。
- Placeholder 扫描：没有使用禁用占位词作为计划内容。
- 类型一致性：所有新增接口都围绕现有 `AdapterContext`、profile、timeline、evaluation 和 UI worker 结构展开。
- 风险控制：所有真实素材和模型权重都限定在本机临时目录、`models/`、`scratch/` 或 `测试视频/`，不进入 Git。
