# Intelligent Voice Over

> A local-first Windows desktop app for AI-assisted video dubbing — re-dub English / Japanese / Korean video dialogue into natural Chinese audio.

![Electron](https://img.shields.io/badge/Electron-31-blue)
![Vue](https://img.shields.io/badge/Vue-3-42b883)
![Python](https://img.shields.io/badge/python-3.10-blue)
![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-orange)
![Platform](https://img.shields.io/badge/platform-Windows-blue)

**English** | [中文](./README.md)

---

## Why IVO

- **Local-first**: The core pipeline runs locally. Model weights never leave your machine, and neither do your video assets.
- **Dual-mode access**: Supports both local models (Demucs / faster-whisper / pyannote / F5-TTS / CosyVoice) and cloud APIs (OpenAI / Deepgram / ElevenLabs / Alibaba Cloud / iFlytek, etc.).
- **Modern desktop UI**: Electron + Vue 3 + FastAPI three-tier architecture with responsive UI. Full workflow from project creation to timeline review — no command line needed.
- **Resumable pipeline**: Each stage records its state independently. If something fails mid-way, fix the environment and resume from the checkpoint without wasting completed work.
- **Built-in compliance**: AI dubbing metadata is automatically embedded on export, with visible watermarks to ensure transparent labeling of AI-generated content.
- **Batch processing**: Process entire seasons of episodes. A single episode failure doesn't block the rest, with a final summary report.

## Architecture

```
┌─────────────────────────────────────────────┐
│            Electron Shell (Main)             │
│   Window lifecycle, start/stop Python service│
├─────────────────────────────────────────────┤
│          Vue 3 Renderer (Frontend)           │
│   Project mgmt / Timeline / Model config     │
├─────────────────────────────────────────────┤
│         FastAPI Python Service (Backend)     │
│   Pipeline orchestration / Adapters / SQLite │
├─────────────────────────────────────────────┤
│            Local Models / HTTP API           │
│   Demucs / faster-whisper / pyannote / F5-TTS│
└─────────────────────────────────────────────┘
```

- **Frontend**: Vue 3 + Vite + Naive UI, TypeScript strict mode
- **Backend**: FastAPI + uvicorn, packaged as standalone executable via PyInstaller
- **Desktop shell**: Electron 31, manages windows and Python service lifecycle
- **Communication**: Frontend calls local Python service via HTTP/WebSocket (127.0.0.1:17000-17999)

## Pipeline

```
Source video
  │
  ├─ 1. Import         Copy source video to project
  ├─ 2. Audio extract   FFmpeg extracts normalized WAV
  ├─ 3. Separation      Demucs / HTTP API → vocals.wav + background.wav
  ├─ 4. ASR             faster-whisper / HTTP API → timestamped segments
  ├─ 5. Diarization     pyannote / HTTP API (optional) → speaker IDs
  ├─ 6. Translation     LM Studio / HTTP API → Chinese text
  ├─ 7. TTS             F5-TTS / CosyVoice / HTTP API → per-segment Chinese audio
  └─ 8. Export          FFmpeg mix background + aligned segments + watermark → final MP4
```

Each stage records its state independently, supporting resumable execution.

## Quick Start

### Option 1: Download Installer (Recommended for Users)

1. Go to the [Releases page](https://github.com/gzyasd/intelligent-voice-over/releases) and download the latest `IVO.Setup.x.x.x.exe`
2. Double-click to run and follow the installer
3. **Install the AI runtime** (required, see "Install AI Runtime" below)
4. Launch IVO from Start Menu or desktop shortcut
5. Configure local models before first use (see "Local Model Setup" below)

> The installer includes FFmpeg and the Python backend runtime — no additional installation required.

#### Install AI Runtime

IVO's local-model pipeline depends on two Python environments: `.venv` (main environment with torch / demucs / faster-whisper / F5-TTS, etc.) and `.venv-pyannote` (speaker diarization). Due to their size (~6 GB combined), they are not bundled in the installer and must be installed separately. Choose one of the two methods:

**Method A: Download prebuilt environment packages (recommended, offline-friendly)**

Due to GitHub's 2 GB single-file limit, the environment packages are uploaded to the Release as split volumes:

1. Main environment `.venv` (~3.5 GB):
   - Download `ivo-venv-portable.zip.01.part`, `ivo-venv-portable.zip.02.part`, and `merge-ivo-venv-portable.bat`
   - Put all three files in the same folder, then double-click `merge-ivo-venv-portable.bat` to merge them into `ivo-venv-portable.zip`
   - Extract the zip and copy the resulting `.venv` folder into the `resources\` directory of the IVO install location
2. Diarization environment `.venv-pyannote` (~2.7 GB):
   - Download `ivo-venv-pyannote-portable.zip.01.part`, `ivo-venv-pyannote-portable.zip.02.part`, and `merge-ivo-venv-pyannote-portable.bat`
   - Merge them the same way to get `ivo-venv-pyannote-portable.zip`, then extract and copy the `.venv-pyannote` folder into `resources\`

After installation, the IVO install directory should look like:

```
IVO/
├── IVO.exe
└── resources/
    ├── python/            (backend service, bundled with installer)
    ├── ffmpeg/bin/        (audio/video processing, bundled with installer)
    ├── .venv/             (main AI environment, manual download)
    └── .venv-pyannote/   (diarization environment, manual download)
```

**Method B: In-app automatic install (online, mirror selectable)**

After launching IVO, if the environments are missing, the Settings page will show a warning. Click "Auto Install Environment", choose a mirror (Official / Tsinghua / Aliyun / USTC), and the wizard will create both venvs and install dependencies with a visible progress UI.

### Option 2: Build from Source (Recommended for Developers)

#### Prerequisites

- Windows 10/11
- [Node.js](https://nodejs.org/) 20+
- [pnpm](https://pnpm.io/) 10+
- [Python](https://www.python.org/) 3.10
- [uv](https://docs.astral.sh/uv/) package manager

#### Install Dependencies

```powershell
git clone <repo-url>
cd Intelligent-Voice-Over

# Install frontend dependencies
pnpm install

# Install Python dependencies
uv sync --dev
```

#### Development Mode

```powershell
# Start frontend dev server and Electron together
pnpm dev
```

#### Build

```powershell
# 1. Build frontend
pnpm run build:frontend

# 2. Package Python backend (PyInstaller)
pnpm run build:python

# 3. Package Electron installer
pnpm run build:win
```

Build artifacts are in `dist/`:
- `IVO Setup x.x.x.exe` — NSIS installer
- `win-unpacked/IVO.exe` — portable version

### Local Model Setup

The project does not bundle model weights. Before using the local model pipeline for the first time, download the following models:

| Stage | Recommended Model | Download Method |
|-------|-------------------|-----------------|
| Separation | Demucs `htdemucs_ft` | Auto-downloaded on first run |
| ASR | faster-whisper `large-v3` | HuggingFace Hub |
| Diarization | pyannote community-1 | Requires accepting HF model terms |
| Translation | LM Studio + Qwen3 | Local HTTP service |
| TTS | F5-TTS | HuggingFace Hub |

Model directory structure:

```
models/
  asr/
    faster-whisper-large-v3/
  diarization/
    pyannote-community-1/
  tts/
    f5-tts/
```

In the desktop app, go to "Model Center", select the model directory, and click "Check Readiness" to verify model integrity.

### FFmpeg

The installer includes FFmpeg. When running from source, the repository's `ffmpeg/bin/` directory also contains FFmpeg — no separate installation needed.

## Desktop App Usage

The desktop app uses a left-side navigation layout:

| Page | Purpose |
|------|---------|
| **Home** | Quick access and recent projects |
| **Project Library** | Manage all `.ivoproj` projects — open, view folder, delete |
| **Current Project** | Generation progress, timeline review, per-segment regeneration, final export |
| **Model Center** | Select model directory, one-click readiness check, manage model schemes |
| **Model Services** | Configure cloud API providers (OpenAI / Deepgram / ElevenLabs, etc.) |
| **Settings** | Project directory, recent projects, user preferences |

Recommended workflow:

1. In "Model Center", select model directory and check readiness
2. Create a new project via the 4-step wizard (select video → select language → select model scheme → confirm)
3. View stage and segment-level progress in "Current Project → Generation Progress"
4. Review in "Timeline" after completion, with per-segment regeneration
5. Confirm and execute final export (with compliance watermark)

## Two Access Modes

### Local Models

Configure local models via model schemes. All inference runs on local GPU/CPU:

| Stage | Recommended Model | Notes |
|-------|-------------------|-------|
| Separation | Demucs `htdemucs_ft` | GPU preferred |
| ASR | faster-whisper `large-v3` | GPU/float16 |
| Diarization | pyannote community-1 | Requires accepting HF model terms |
| Translation | LM Studio + Qwen3 | Local HTTP service |
| TTS | F5-TTS / CosyVoice | F5 weights are CC-BY-NC, need alternative for commercial use |

### Cloud APIs

Describe HTTP APIs via `ApiAdapterProfile`. Any stage can be replaced with a cloud service. Built-in cloud providers:

| Provider | Supported Stages |
|----------|-----------------|
| OpenAI | ASR + Diarization + TTS |
| Deepgram | ASR |
| AudioShake | Separation |
| LALAL.AI | Separation |
| Alibaba Cloud Bailian | ASR |
| Alibaba Cloud Qwen-TTS | TTS |
| ElevenLabs | TTS |
| Anthropic | Translation |
| OpenAI-compatible | Translation |
| iFlytek Open Platform | ASR + Diarization |

## Project Structure

```
{project}.ivoproj/
  project.json       Project metadata
  segments.sqlite    Timeline segment storage
  jobs.sqlite        Stage execution state
  speakers.json      Speaker configuration
  settings.json      Project settings
  assets/            Source video, extracted audio
  work/              Vocals, background, generated segment audio
  renders/           Final output videos
```

## Development

```powershell
# Frontend type checking
pnpm run typecheck

# Frontend unit tests
pnpm test

# Python linting
uv run ruff check .

# Python type checking (strict mode)
uv run mypy src

# Python tests
uv run pytest
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Desktop shell | Electron 31 |
| Frontend | Vue 3 + Vite + Naive UI + TypeScript |
| Backend | FastAPI + uvicorn + Pydantic v2 |
| Storage | SQLite (native sqlite3, no ORM) |
| Templating | Jinja2 (SandboxedEnvironment + StrictUndefined) |
| HTTP | httpx |
| Packaging | PyInstaller (Python) + electron-builder (Electron) |

## License

This project's source code is licensed under **PolyForm Noncommercial License 1.0.0**. You may view, study, modify, run, and distribute this project's code for non-commercial purposes, but **commercial use requires written permission from the author**.

> PolyForm Noncommercial License is not an OSI-approved open source license because it restricts commercial use. This project adopts a "source-available / non-commercial license" distribution model.

Commercial use includes but is not limited to: paid products, SaaS services, enterprise internal production deployment, paid delivery, commercial project integration, paid deployment/consulting/operations. See [COMMERCIAL-LICENSE.md](./COMMERCIAL-LICENSE.md) for commercial licensing.

**Third-party model notice**: F5-TTS code is MIT, but the default pretrained weights are CC-BY-NC. Commercial use requires switching to a model or service with an appropriate license. Third-party model licenses are independent and do not automatically adopt the same license as this project's PolyForm Noncommercial code.

## Contributing

Before contributing, please read:

- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)
- [SECURITY.md](./SECURITY.md)
- [docs/compliance-and-licenses.md](./docs/compliance-and-licenses.md)

Please do not commit real API keys, tokens, unauthorized video/audio assets, or model weights to the repository.

## More Documentation

- [Local Model Setup](./docs/local-model-setup.md)
- [Local Command Profile Guide](./docs/local-model-command-profiles.md)
- [HTTP API Profile Guide](./docs/http-api-profiles.md)
- [Compliance & Licenses](./docs/compliance-and-licenses.md)
