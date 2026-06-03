# 剩余任务与本地模型落地 Implementation Plan

> **给后续执行者：** 本计划使用复选框（`- [ ]`）追踪实施进度。先完成可验证的小闭环，再扩大到真实剧集片段；不要等所有功能做完才提交和推送。

**Goal:** 把当前可测试的 mock/adapter 工程骨架推进到“真实本地模型可跑、质量可评估、用户可配置、可发布”的开源桌面软件。

**Architecture:** 继续保持本地优先、adapter 优先的结构：真实模型不直接塞进核心流水线，而是通过 `LocalCommandAdapter`、HTTP profile、模型登记和 UI 设置接入。每个阶段先形成可独立验证的命令合约，再接入桌面端和整片导出。

**Tech Stack:** Python 3.10、uv、PySide6、pytest、ruff、mypy、FFmpeg、Faster-Whisper/WhisperX、Demucs/UVR、pyannote.audio、Fun-CosyVoice/CosyVoice、F5-TTS、GPT-SoVITS、Qwen3/vLLM/SGLang 或自定义 HTTP API。

---

## 当前状态判断

截至 2026-06-03，项目已经完成 v1 工程骨架、mock 端到端流水线、本地命令 adapter、HTTP adapter、桌面 UI 基础流程、时间线编辑、单句重生成、最终导出、合规闸门和开源仓库准备。

按“能否作为日常真实配音工具使用”估算，当前整体完成度约为 **55%-60%**。如果只看工程底座和可测试接口，完成度约为 **80%-85%**；真正缺口主要在真实模型落地、真实样片质量评估、模型下载/配置体验、Windows 发布包和长视频稳定性。

## 剩余任务总览

### P0：真实本地模型最小闭环

- [ ] 建立本地模型目录和下载规范，确认所有模型权重不进入 Git。
- [ ] 用真实 `faster-whisper` 跑通英文、日文、韩文 ASR。
- [ ] 用真实 `demucs` 跑通人声/背景音分离。
- [ ] 用真实 TTS/音色克隆引擎生成中文对白，优先评估 Fun-CosyVoice3，其次 F5-TTS、GPT-SoVITS。
- [ ] 用 1-3 分钟授权样片跑完整 `local-preview`，输出可观看视频。

### P1：质量控制和用户可配置体验

- [ ] 增强 `doctor-models`，输出每个模型的安装状态、下载渠道、许可证提示和最小验证命令。
- [ ] 增加真实模型 profile 模板，覆盖 ASR、分离、说话人分离、翻译、TTS。
- [ ] 在 UI 中加入模型配置向导、profile 导入、日志查看和错误定位。
- [ ] 加入质量面板：时长偏差、空白音频、ASR 低置信度、说话人冲突、TTS 失败、参考音频缺失。
- [ ] 建立真实样片评估报告格式，记录每轮模型组合的主观和客观结果。

### P2：发布和长期稳定性

- [ ] 完成 Windows 打包验证，生成 GitHub Release 草稿。
- [ ] 完成示例素材说明和用户文档，不上传未授权剧集片段。
- [ ] 加入批处理/剧集级工作流：多集排队、失败续跑、导出目录管理。
- [ ] 建立线上 API provider 示例文档，覆盖 OpenAI-compatible、普通 JSON API、multipart 文件上传。
- [ ] 对长视频做恢复性测试：中断、重启、局部重生成、最终导出一致性。

## 推荐本地模型组合

### 首选高质量组合

| 阶段 | 推荐模型/工具 | 下载渠道 | 推荐理由 | 注意事项 |
| --- | --- | --- | --- | --- |
| 人声分离 | Demucs `htdemucs_ft` 或 `htdemucs` | GitHub: <https://github.com/facebookresearch/demucs>；PyPI: `pip install -U demucs` | 已有命令脚本骨架，适合先打通人声/背景音分轨 | 原仓库已归档，仍可作为 P0 基线；遇到维护问题再评估 fork 或 UVR5 |
| ASR | `faster-whisper` + `Systran/faster-whisper-large-v3` | GitHub: <https://github.com/SYSTRAN/faster-whisper>；HF: <https://huggingface.co/Systran/faster-whisper-large-v3> | 对英/日/韩转写稳定，速度和显存占用比原始 Whisper 更适合桌面软件 | NVIDIA GPU 推荐 `float16`；8GB 显存可尝试 `int8_float16` |
| ASR 快速预览 | `openai/whisper-large-v3-turbo` 或 `Systran/faster-distil-whisper-large-v3` | HF: <https://huggingface.co/openai/whisper-large-v3-turbo>；HF: <https://huggingface.co/Systran/faster-distil-whisper-large-v3> | 适合预览模式，速度更好 | Turbo 有轻微质量损失；distil 主要偏英文，需要单独验证日/韩 |
| 词级对齐/说话人辅助 | WhisperX | GitHub: <https://github.com/m-bain/whisperX> | 能补充词级时间戳和 diarization，利于配音时长控制 | 依赖 CUDA 和 pyannote，Windows 环境要单独验证 |
| 说话人分离 | `pyannote/speaker-diarization-community-1`，备选 `speaker-diarization-3.1` | HF: <https://huggingface.co/pyannote/speaker-diarization-community-1>；HF: <https://huggingface.co/pyannote/speaker-diarization-3.1> | Community-1 支持离线使用且更方便和转写时间戳对齐 | 需要 Hugging Face 登录并接受模型条件；不要把 token 写进仓库 |
| 中文 TTS/音色克隆首选 | `FunAudioLLM/Fun-CosyVoice3-0.5B-2512` | GitHub: <https://github.com/FunAudioLLM/CosyVoice>；HF: <https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512>；ModelScope: <https://modelscope.cn/models/FunAudioLLM/Fun-CosyVoice3-0.5B-2512> | Apache-2.0，支持中英日韩等 9 种语言、跨语种 zero-shot、情绪/语速等 instruct 控制，适合本项目目标 | 先做命令行 wrapper，再接 UI；中文文本规范化资源可选下载 |
| 中文 TTS/音色克隆备选 | `FunAudioLLM/CosyVoice2-0.5B` | HF: <https://huggingface.co/FunAudioLLM/CosyVoice2-0.5B>；ModelScope: <https://modelscope.cn/models/iic/CosyVoice2-0.5B> | 成熟度较高，已有大量示例和社区经验 | 如果 CosyVoice3 在本机不稳定，用它做稳定备选 |
| 中文 TTS/音色克隆备选 | F5-TTS | GitHub: <https://github.com/SWivid/F5-TTS>；HF: <https://huggingface.co/SWivid/F5-TTS> | 音色克隆和多说话人生成能力强，已有项目脚本骨架 | 代码 MIT，但预训练模型是 CC-BY-NC，商用要谨慎 |
| 精调型音色克隆备选 | GPT-SoVITS | GitHub: <https://github.com/RVC-Boss/GPT-SoVITS> | 5 秒 zero-shot、1 分钟 few-shot，适合追求特定角色音色相似度 | 环境更重，适合 P1/P2；先通过外部 API 或命令 wrapper 接入 |
| 本地翻译 | Qwen3-8B / Qwen3-14B，或同系列量化模型 | HF: <https://huggingface.co/Qwen/Qwen3-8B>；HF: <https://huggingface.co/Qwen/Qwen3-14B>；GitHub: <https://github.com/QwenLM/Qwen3> | 支持 100+ 语言和翻译，适合把英/日/韩台词转成自然中文 | P0 可先用 HTTP 翻译；本地 Qwen 适合通过 vLLM/SGLang/OpenAI-compatible API 接入 |

### 推荐下载目录

模型权重建议统一放在项目外或仓库忽略目录下，例如：

```text
F:\GZYproject\Intelligent-Voice-Over\models\
  asr\
    faster-whisper-large-v3\
    whisper-large-v3-turbo\
  separation\
    demucs\
  diarization\
    pyannote-community-1\
  tts\
    Fun-CosyVoice3-0.5B\
    CosyVoice2-0.5B\
    F5-TTS\
  llm\
    Qwen3-8B\
```

下载命令示例：

```powershell
huggingface-cli download Systran/faster-whisper-large-v3 --local-dir .\models\asr\faster-whisper-large-v3
huggingface-cli download openai/whisper-large-v3-turbo --local-dir .\models\asr\whisper-large-v3-turbo
huggingface-cli download FunAudioLLM/Fun-CosyVoice3-0.5B-2512 --local-dir .\models\tts\Fun-CosyVoice3-0.5B
huggingface-cli download FunAudioLLM/CosyVoice2-0.5B --local-dir .\models\tts\CosyVoice2-0.5B
huggingface-cli download SWivid/F5-TTS --local-dir .\models\tts\F5-TTS
huggingface-cli download Qwen/Qwen3-8B --local-dir .\models\llm\Qwen3-8B
```

国内网络优先使用 ModelScope 时，CosyVoice 可用以下 Python 片段下载：

```python
from modelscope import snapshot_download

snapshot_download("FunAudioLLM/Fun-CosyVoice3-0.5B-2512", local_dir="models/tts/Fun-CosyVoice3-0.5B")
snapshot_download("iic/CosyVoice2-0.5B", local_dir="models/tts/CosyVoice2-0.5B")
```

pyannote 模型通常需要先登录 Hugging Face 并接受模型条件：

```powershell
huggingface-cli login
huggingface-cli download pyannote/speaker-diarization-community-1 --local-dir .\models\diarization\pyannote-community-1
```

## 分阶段实施计划

### Task 1：模型环境与下载规范

**Files:**
- Modify: `src/ivo/environment.py`
- Modify: `src/ivo/cli.py`
- Modify: `docs/local-model-command-profiles.md`
- Create: `docs/local-model-setup.md`
- Test: `tests/test_smoke.py`
- Test: `tests/examples/test_real_command_skeletons.py`

- [ ] **Step 1: 增强 `doctor-models` 输出**

  让 `uv run ivo doctor-models` 输出每个阶段的推荐包、是否已安装、下载渠道、许可证提醒、模型目录是否存在。输出中至少包含 `faster-whisper`、`demucs`、`pyannote.audio`、`f5_tts`、`cosyvoice`、`transformers`、`vllm`。

- [ ] **Step 2: 为模型权重目录加文档约束**

  在 `docs/local-model-setup.md` 写清楚：模型权重不进入 Git；真实素材不进入 Git；API key 不进入 Git；可用 `models/`、`sample_media/`、`scratch/` 做本机目录。

- [ ] **Step 3: 验证**

  ```powershell
  uv run ivo doctor
  uv run ivo doctor-models
  uv run pytest tests/test_smoke.py tests/examples/test_real_command_skeletons.py -v
  ```

- [ ] **Step 4: 提交和推送**

  ```powershell
  git add src/ivo/environment.py src/ivo/cli.py docs/local-model-command-profiles.md docs/local-model-setup.md tests/test_smoke.py tests/examples/test_real_command_skeletons.py
  git commit -m "docs: add local model setup guidance"
  git push
  ```

### Task 2：真实 ASR profile 验收

**Files:**
- Modify: `examples/local_commands/faster_whisper_asr.py`
- Modify: `examples/local_command_profiles.real_dry_run.json`
- Create: `examples/local_command_profiles.real_asr.json`
- Test: `tests/examples/test_local_command_examples.py`
- Test: `tests/test_local_command_pipeline.py`

- [ ] **Step 1: 固定 ASR 输出合约**

  `faster_whisper_asr.py` 的真实模式必须输出：

  ```json
  {
    "segments": [
      {
        "id": "seg-001",
        "start_ms": 100,
        "end_ms": 2100,
        "text": "Well, hi.",
        "speaker_id": "speaker-1"
      }
    ]
  }
  ```

- [ ] **Step 2: 增加真实 ASR profile**

  `examples/local_command_profiles.real_asr.json` 使用 `large-v3` 作为高质量默认值，允许通过 profile 把 `--model` 改为 `turbo`、`distil-large-v3` 或本地模型路径。

- [ ] **Step 3: 样片验证**

  ```powershell
  uv run ivo local-preview .\sample_media\en_1min.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_asr.json --project-name "ASR EN" --source-language en --no-watermark
  uv run ivo local-preview .\sample_media\ja_1min.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_asr.json --project-name "ASR JA" --source-language ja --no-watermark
  uv run ivo local-preview .\sample_media\ko_1min.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_asr.json --project-name "ASR KO" --source-language ko --no-watermark
  ```

- [ ] **Step 4: 自动化验证**

  ```powershell
  uv run pytest tests/examples/test_local_command_examples.py tests/test_local_command_pipeline.py -v
  ```

### Task 3：真实人声分离 profile 验收

**Files:**
- Modify: `examples/local_commands/demucs_separate.py`
- Create: `examples/local_command_profiles.real_separation_asr.json`
- Test: `tests/examples/test_real_command_skeletons.py`
- Test: `tests/pipeline/test_separate_audio.py`

- [ ] **Step 1: 支持 Demucs 模型名和 two-stems 参数**

  默认使用 `--two-stems=vocals` 和 `-n htdemucs`。高质量模式允许改为 `-n htdemucs_ft`。

- [ ] **Step 2: 输出路径标准化**

  保证输出 JSON 永远包含：

  ```json
  {
    "vocals_path": "path/to/vocals.wav",
    "background_path": "path/to/background.wav"
  }
  ```

- [ ] **Step 3: 样片验证**

  ```powershell
  uv run ivo local-preview .\sample_media\en_1min.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_separation_asr.json --project-name "Separation ASR EN" --source-language en --no-watermark
  ```

- [ ] **Step 4: 自动化验证**

  ```powershell
  uv run pytest tests/pipeline/test_separate_audio.py tests/examples/test_real_command_skeletons.py -v
  ```

### Task 4：说话人分离与时间线映射

**Files:**
- Create: `examples/local_commands/pyannote_diarization.py`
- Create: `examples/local_command_profiles.real_diarization.json`
- Modify: `src/ivo/pipeline/transcribe.py`
- Test: `tests/pipeline/test_transcribe.py`
- Test: `tests/examples/test_local_command_examples.py`

- [ ] **Step 1: 新增 pyannote 命令 wrapper**

  wrapper 输入 `--audio`、`--model`、`--hf-token-env`、`--out`，输出：

  ```json
  {
    "segments": [
      {
        "start_ms": 0,
        "end_ms": 1200,
        "speaker_id": "speaker-1"
      }
    ]
  }
  ```

- [ ] **Step 2: 映射 ASR 片段**

  当 diarization 与 ASR 片段重叠时，选择重叠时长最大的 speaker；没有匹配时保留 `speaker-1` 并加入 `speaker_unmatched` quality flag。

- [ ] **Step 3: 样片验证**

  ```powershell
  $env:HF_TOKEN="你的 Hugging Face token"
  uv run ivo local-preview .\sample_media\multi_speaker_1min.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_diarization.json --project-name "Diarization EN" --source-language en --no-watermark
  ```

- [ ] **Step 4: 自动化验证**

  ```powershell
  uv run pytest tests/pipeline/test_transcribe.py tests/examples/test_local_command_examples.py -v
  ```

### Task 5：本地翻译模型和风格提示

**Files:**
- Modify: `src/ivo/pipeline/translate.py`
- Create: `examples/http_translation_openai_compatible.example.json`
- Create: `examples/local_command_profiles.real_translation_qwen.json`
- Test: `tests/pipeline/test_translate.py`
- Test: `tests/examples/test_http_profile_examples.py`

- [ ] **Step 1: 固定翻译输出字段**

  翻译阶段建议输出：

  ```json
  {
    "target_text": "嗯，你好。",
    "emotion": "warm",
    "style_prompt": "温和、自然、带轻微笑意，保留短暂停顿"
  }
  ```

- [ ] **Step 2: 增加 OpenAI-compatible translation profile**

  让本地 vLLM/SGLang 运行的 Qwen3 或线上 API 共用同一个 HTTP profile。请求中必须包含 `source_language`、`target_language`、`speaker_id`、`source_text`、`duration_ms`。

- [ ] **Step 3: 风格提示规则**

  翻译 prompt 要明确：保留自然语气词，但不要机械逐字塞入；中文台词应适合原片段时长；日剧/韩剧常见停顿、吸气、犹豫、笑声可通过 `style_prompt` 传给 TTS。

- [ ] **Step 4: 自动化验证**

  ```powershell
  uv run pytest tests/pipeline/test_translate.py tests/examples/test_http_profile_examples.py -v
  ```

### Task 6：真实 TTS/音色克隆引擎接入

**Files:**
- Modify: `examples/local_commands/f5_tts_command.py`
- Create: `examples/local_commands/cosyvoice_tts.py`
- Create: `examples/local_command_profiles.real_tts_cosyvoice.json`
- Create: `examples/local_command_profiles.real_tts_f5.json`
- Test: `tests/examples/test_real_command_skeletons.py`
- Test: `tests/pipeline/test_synthesize.py`

- [ ] **Step 1: 先接 Fun-CosyVoice3**

  `cosyvoice_tts.py` 输入 `--text`、`--reference-audio`、`--reference-text`、`--style-prompt`、`--duration-ms`、`--audio-out`、`--json-out`、`--model-dir`。

- [ ] **Step 2: 保持 TTS 输出合约**

  所有 TTS wrapper 最终输出：

  ```json
  {
    "audio_path": "path/to/generated.wav",
    "duration_ms": 1000
  }
  ```

- [ ] **Step 3: 参考音频策略**

  优先使用同 speaker 已批准片段；没有批准片段时使用当前源片段；无可用音频时返回清晰错误并标记 `missing_reference_audio`。

- [ ] **Step 4: 样片验证**

  ```powershell
  uv run ivo local-preview .\sample_media\en_1min.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_tts_cosyvoice.json --project-name "CosyVoice EN" --source-language en --no-watermark
  ```

- [ ] **Step 5: 自动化验证**

  ```powershell
  uv run pytest tests/pipeline/test_synthesize.py tests/examples/test_real_command_skeletons.py -v
  ```

### Task 7：真实样片评测与质量报告

**Files:**
- Create: `docs/evaluation/real-video-evaluation.md`
- Create: `docs/evaluation/runs/README.md`
- Modify: `README.md`

- [ ] **Step 1: 建立评测素材规范**

  评测素材只能使用授权样片、本地私有文件或公开可测试素材；不要上传美剧、日剧、韩剧片段到仓库。

- [ ] **Step 2: 建立评分表**

  每个样片记录：源语言、时长、人物数、模型组合、ASR 错误、翻译自然度、音色相似度、情绪一致性、时长匹配、背景音保留、最终可看性。

- [ ] **Step 3: 建立通过标准**

  P0 通过标准：1 分钟片段能完整导出；无崩溃；主要对白可理解；背景音存在；TTS 片段没有大面积空白。P1 通过标准：3-5 分钟多说话人片段可完成审核、局部重生成和最终导出。

- [ ] **Step 4: 文档提交**

  ```powershell
  git add docs/evaluation README.md
  git commit -m "docs: add real video evaluation plan"
  git push
  ```

### Task 8：UI 模型配置和错误定位

**Files:**
- Modify: `src/ivo/ui/model_settings.py`
- Modify: `src/ivo/ui/main_window.py`
- Modify: `src/ivo/ui/workers.py`
- Test: `tests/ui/test_main_window_error_handling.py`
- Test: `tests/ui/test_main_window_local_preview.py`

- [ ] **Step 1: Profile 导入**

  UI 中允许选择 `examples/*.json` 或用户自定义 profile，并显示每个阶段当前使用 local、http 还是 mock。

- [ ] **Step 2: 模型状态面板**

  显示 `doctor-models` 的检查结果：缺少哪个包、哪个模型目录不存在、哪个 token 没设置、哪个 license 未确认。

- [ ] **Step 3: 错误定位**

  adapter 失败时 UI 显示阶段、provider、命令、退出码、stderr 摘要、输出 JSON 路径和可重试建议。

- [ ] **Step 4: 自动化验证**

  ```powershell
  uv run pytest tests/ui/test_main_window_error_handling.py tests/ui/test_main_window_local_preview.py -v
  ```

### Task 9：长视频恢复性和批处理

**Files:**
- Modify: `src/ivo/core/jobs.py`
- Modify: `src/ivo/pipeline/orchestrator.py`
- Modify: `src/ivo/ui/main_window.py`
- Test: `tests/pipeline/test_orchestrator.py`
- Test: `tests/core/test_project.py`

- [ ] **Step 1: 阶段级续跑**

  每个阶段写入状态，重启后能从已完成阶段继续；失败片段只重跑该片段，不清空整条时间线。

- [ ] **Step 2: 批处理入口**

  CLI 增加批处理命令时，输入目录中的多个视频按队列处理，输出到独立 `.ivoproj` 和 `renders/`。

- [ ] **Step 3: 自动化验证**

  ```powershell
  uv run pytest tests/pipeline/test_orchestrator.py tests/core/test_project.py -v
  ```

### Task 10：Windows 发布包和开源发布节奏

**Files:**
- Modify: `docs/windows-packaging.md`
- Modify: `README.md`
- Modify: `.github/workflows/ci.yml`
- Test: `tests/test_windows_packaging.py`

- [ ] **Step 1: 打包验证**

  按 `docs/windows-packaging.md` 生成本地 Windows 可执行包，确认 UI 可启动、FFmpeg 可检测、mock preview 可导出。

- [ ] **Step 2: Release 草稿**

  GitHub Release 中明确：不内置模型权重；不内置影视素材；用户需自行确认模型许可证和素材授权。

- [ ] **Step 3: CI 验证**

  ```powershell
  uv run pytest
  uv run ruff check .
  uv run mypy src
  ```

- [ ] **Step 4: 提交、推送和创建发布草稿**

  ```powershell
  git add docs/windows-packaging.md README.md .github/workflows/ci.yml tests/test_windows_packaging.py
  git commit -m "chore: prepare windows release packaging"
  git push
  ```

## 下一步建议执行顺序

1. 先做 Task 1，解决模型环境和下载说明，避免后续一边接模型一边猜路径。
2. 再做 Task 2 和 Task 3，让真实 ASR + 分离先跑起来，这是后续 TTS 质量的地基。
3. 然后做 Task 6，优先接 Fun-CosyVoice3；TTS 是这个产品自然度的核心，应该尽早真实验收。
4. 接着做 Task 4 和 Task 5，把说话人、翻译风格、语气词、情绪提示串起来。
5. 最后做 Task 7-10，把评测、UI、长视频、发布包补齐。

## 验收口径

P0 完成时，应满足：

- [ ] `uv run ivo doctor` 和 `uv run ivo doctor-models` 能给出清楚的环境状态。
- [ ] 至少一个英文、一个日文或韩文授权样片可通过真实本地模型导出视频。
- [ ] 输出视频包含中文配音、背景音、可选水印和 AI 配音元数据。
- [ ] 失败时 UI/CLI 能指出具体阶段和 provider，不只抛 Python traceback。
- [ ] 所有代码变更通过 `uv run pytest`、`uv run ruff check .`、`uv run mypy src`。

P1 完成时，应满足：

- [ ] 3-5 分钟多说话人样片可完成审核、单句重生成和最终导出。
- [ ] 用户能在 UI 中选择本地模型或线上 API profile。
- [ ] 质量报告能说明每个模型组合的优劣，而不是只凭感觉判断。
- [ ] GitHub 仓库保持开源、可复现、无模型权重、无真实密钥、无未授权素材。

## 许可证与合规提醒

- 本项目代码采用 MIT License，但第三方模型各自有许可证，不能用项目许可证覆盖模型许可证。
- F5-TTS 代码是 MIT，预训练模型是 CC-BY-NC；商业用途要避免默认推荐为商用方案。
- Fun-CosyVoice3 当前标注 Apache-2.0，更适合作为首选本地 TTS 评估对象，但仍需在下载和使用前再次确认模型卡。
- pyannote 模型需要用户登录并接受条件，不能把 Hugging Face token 写入仓库或 profile。
- 对美剧、日剧、韩剧素材，只处理用户拥有授权的本地文件；评测报告和 GitHub 仓库不上传原片、切片或可识别的未授权音频。
