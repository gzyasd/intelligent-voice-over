# Intelligent Voice Over

> A local-first Windows desktop app for AI-assisted video dubbing — re-dub English / Japanese / Korean video dialogue into natural Chinese audio.

![Python](https://img.shields.io/badge/python-3.10-blue)
![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-orange)
![Platform](https://img.shields.io/badge/platform-Windows-blue)
![UI](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt%206-green)

**English** | [中文](./README.md)

---

## Why IVO

- **Local-first**: The core pipeline runs locally. Model weights are never uploaded, and your video assets never leave your machine.
- **Dual-mode integration**: Supports both local models (Demucs / faster-whisper / pyannote / F5-TTS / CosyVoice) and cloud APIs (OpenAI / Deepgram / ElevenLabs / Alibaba Cloud / iFlytek, etc.).
- **Visual desktop app**: A PySide6 single-window application — from project creation to timeline review, the entire workflow is visual, no command line required.
- **Resumable pipeline**: Each stage records its state independently. If a run fails mid-way, fix the environment and resume from the last checkpoint — no wasted work.
- **Built-in compliance**: Exports automatically embed AI dubbing metadata and support visible watermarks, ensuring transparent labeling of AI-generated content.
- **Batch processing**: Process an entire season of episodes in one run. Individual failures don't block the rest, with a final summary report.

## Pipeline

```
Source Video
  │
  ├─ 1. Import          Copy source video into project
  ├─ 2. Audio Extract    FFmpeg extracts normalized WAV
  ├─ 3. Separation      Demucs / HTTP API → vocals.wav + background.wav
  ├─ 4. ASR              faster-whisper / HTTP API → timestamped segments
  ├─ 5. Diarization      pyannote / HTTP API (optional) → speaker IDs
  ├─ 6. Translation       LM Studio / HTTP API → Chinese text
  ├─ 7. TTS              F5-TTS / CosyVoice / HTTP API → per-segment Chinese audio
  └─ 8. Mix & Export     FFmpeg mixes background + aligned segments + watermark → final MP4
```

Each stage records its state independently and supports `--resume-existing` for checkpoint recovery.

## Quick Start

### Prerequisites

- Windows 10/11
- Python 3.10
- [uv](https://docs.astral.sh/uv/) package manager

> FFmpeg is already bundled in the repository's `ffmpeg/bin/` directory — ready to use after cloning, no separate installation or environment variable configuration needed.

### Installation

```powershell
git clone <repo-url>
cd Intelligent-Voice-Over
uv sync --dev
```

### Environment Diagnostics

```powershell
uv run ivo doctor
```

### Launch Desktop UI

```powershell
uv run python -m ivo.app
```

### Generate Test Sample (no real footage)

```powershell
uv run python .\scripts\create_sample_media.py --output-dir .\sample_media
```

### About FFmpeg

The repository already bundles FFmpeg 8.0.1 essentials build (in `ffmpeg/bin/`), covering all pipeline needs including audio extraction and video mix/export. The program looks for FFmpeg in this priority order:

1. Project-bundled `ffmpeg/bin/` (default, works out of the box)
2. `IVO_FFMPEG_PATH` environment variable (full path)
3. `IVO_FFMPEG_DIR` environment variable (directory)
4. System PATH

To use a different FFmpeg version, simply overwrite the files in `ffmpeg/bin/`. The portable build also automatically includes this directory.

## Desktop App

The desktop app uses a left-sidebar navigation layout:

| Page | Purpose |
|------|---------|
| **Home** | Quick access and recent projects |
| **Project Library** | Manage all `.ivoproj` projects — open, browse folder, delete |
| **Current Project** | Generation progress, timeline review, per-segment regeneration, final export |
| **Model Center** | Select model directory, one-click readiness check, manage model schemes |
| **Model Services** | Configure cloud API providers (OpenAI / Deepgram / ElevenLabs, etc.) |
| **Settings** | Project directory, recent projects, user preferences |

Recommended workflow:

1. Select a model directory in **Model Center** and run a one-click readiness check
2. Create a new project via the 4-step wizard (select video → choose language → choose model scheme → confirm)
3. Monitor stage and sentence-level progress in **Current Project → Generation Progress**
4. Review in the **Timeline** after generation — regenerate individual segments as needed
5. Confirm and execute final export (includes compliance watermark)

## CLI Usage

### Mock Preview (no real models required)

```powershell
uv run ivo mock-preview .\sample.mp4 .\demo-output --project-name "Episode 01" --source-language en
```

### Local Model Preview

```powershell
# CPU small preview
uv run ivo local-preview .\sample.mp4 ^
  --profiles .\examples\local_command_profiles.real_separation_asr_tts_f5_cpu_small.json ^
  --project-name "Episode 01" --source-language ja ^
  --require-readiness --models-dir .\models --resume-existing --no-watermark

# GPU full quality
uv run ivo local-preview .\sample.mp4 ^
  --profiles .\examples\local_command_profiles.real_full_gpu_f5_diarization.json ^
  --translation-profile .\examples\http_translation_lm_studio_qwen36_35b.example.json ^
  --project-name "Full GPU Episode 01" --source-language ja ^
  --require-readiness --models-dir .\models --resume-existing --no-watermark
```

### Batch Processing

```powershell
uv run ivo batch-local-preview .\episodes ^
  --profiles .\examples\local_command_profiles.real_dry_run.json ^
  --source-language en --no-watermark ^
  --report .\demo-output\batch-report.json --skip-existing
```

### Profile Validation

```powershell
uv run ivo validate-local-profiles .\examples\local_command_profiles.real_dry_run.json --json
uv run ivo check-local-readiness .\examples\local_command_profiles.real_full_gpu_f5_diarization.json --models-dir .\models --json
```

## Two Integration Modes

### Local Models

The project does not bundle model weights. Configure local models via model schemes:

```powershell
uv run ivo model setup-plan --models-dir .\models
uv run ivo model write-setup-script --models-dir .\models
```

Or select a model directory directly in the desktop **Model Center** and run a one-click check.

| Stage | Recommended Model | Notes |
|-------|-------------------|-------|
| Separation | Demucs `htdemucs_ft` | GPU preferred |
| ASR | faster-whisper `large-v3` | GPU/float16 |
| Diarization | pyannote community-1 | Requires accepting HF model terms |
| Translation | LM Studio + Qwen3 | Local HTTP service |
| TTS | F5-TTS / CosyVoice | F5 weights are CC-BY-NC; replace for commercial use |

### Cloud APIs

Describe HTTP APIs via `ApiAdapterProfile`. Every stage can be replaced with a cloud service:

```powershell
# Add an HTTP adapter
uv run ivo adapter add-http .\adapters.json ^
  --id translator --stage translation ^
  --url https://api.example.test/translate ^
  --response target_text=$.text

# Use HTTP translation instead of local
uv run ivo local-preview .\sample.mp4 .\demo-output ^
  --profiles .\examples\local_command_profiles.mock.json ^
  --translation-profile .\examples\http_translation_profile.example.json ^
  --translation-var api_key=YOUR_API_KEY ^
  --project-name "HTTP Translation" --source-language ja
```

Built-in cloud provider support:

| Provider | Supported Stages |
|----------|-----------------|
| OpenAI | ASR + Diarization + TTS |
| Deepgram | ASR |
| AudioShake | Separation |
| LALAL.AI | Separation |
| Alibaba Cloud (Bailian) | ASR |
| Alibaba Cloud Qwen-TTS | TTS |
| ElevenLabs | TTS |
| Anthropic | Translation |
| OpenAI-compatible | Translation |
| iFlytek | ASR + Diarization |

## Project Structure

```
{project}.ivoproj/
  project.json       Project metadata
  segments.sqlite    Timeline segment storage
  jobs.sqlite        Stage execution state
  speakers.json      Speaker profiles
  settings.json      Project settings
  assets/            Source video, extracted audio
  work/              Vocals, background, generated segment audio
  renders/           Final output videos
```

## Development

```powershell
# Run all tests
uv run pytest

# Lint
uv run ruff check .

# Type check (strict mode)
uv run mypy src

# Windows packaging (dry run)
uv run python scripts/build_windows_package.py --dry-run --output-dir dist
```

## License

This project is licensed under **PolyForm Noncommercial License 1.0.0**. You may view, study, modify, run, and distribute this project's code for noncommercial purposes, but **commercial use requires prior written authorization from the copyright holder**.

> PolyForm Noncommercial License is not an OSI-approved open source license because it restricts commercial use. This project is released under a "source-available / noncommercial license" model.

Commercial use includes but is not limited to: paid products, SaaS services, enterprise production deployment, paid delivery, commercial project integration, paid deployment/consulting/operations. See [COMMERCIAL-LICENSE.md](./COMMERCIAL-LICENSE.md) for commercial licensing details.

**Third-party model notice**: F5-TTS code is MIT-licensed, but its default pretrained weights are CC-BY-NC. You must replace them with suitably licensed weights or services before commercial use. Third-party model licenses are independent and do not automatically inherit the PolyForm Noncommercial license of this project.

## Contributing

Please read the following before contributing:

- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)
- [SECURITY.md](./SECURITY.md)
- [docs/compliance-and-licenses.md](./docs/compliance-and-licenses.md)

Do not submit real API keys, tokens, unauthorized video/audio footage, or model weights to the repository.

## Further Documentation

- [Local Model Setup](./docs/local-model-setup.md)
- [Local Command Profile Guide](./docs/local-model-command-profiles.md)
- [HTTP API Profile Guide](./docs/http-api-profiles.md)
- [Desktop UI Guide](./docs/ui-local-preview.md)
- [Windows Packaging](./docs/windows-packaging.md)
- [Compliance & Licenses](./docs/compliance-and-licenses.md)
