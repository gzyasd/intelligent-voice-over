# AGENTS.md

This file provides guidance to AI coding agents when working in this repository.

## 项目概述

Intelligent Voice Over (`ivo`) 是一个本地优先的 Windows 桌面端 AI 视频配音工具。它将英文/日文/韩文视频对白重新配成自然的中文音频，同时支持本地模型流水线和自定义 HTTP API 适配器两种接入模式。

当前主架构：

- 桌面壳：Electron
- 前端：Vue 3 + Vite + TypeScript + Naive UI
- 后端：FastAPI + uvicorn
- Python 包路径：`src/ivo`
- 服务端路径：`server`
- Python 版本限定：`>=3.10,<3.11`
- Python 包管理器：`uv`
- 前端包管理器：`pnpm`

旧 PySide6 桌面 UI 已移除。不要重新引入 `src/ivo/ui`、`ivo.app`、`PySide6` 或旧的 `scripts/build_windows_package.py` 打包流程。

## 常用命令

```powershell
# 安装/同步 Python 依赖
uv sync --dev

# 安装前端依赖
pnpm install

# 启动 Electron/Vue 开发模式
pnpm dev

# 启动 Python 后端
uv run python scripts/ivo_server_entry.py

# 一键安装所有本地模型依赖（含 pyannote.audio 独立环境）
.\scripts\setup-local-env.ps1

# 安装本地模型权重（需先接受 Hugging Face 模型条款）
.\scripts\setup-local-models.ps1

# Python 测试
uv run pytest

# 前端测试
pnpm test

# Python 代码检查
uv run ruff check server/ src/ tests/

# Python 类型检查
uv run mypy src server

# 前端类型检查
pnpm run typecheck

# 前端构建
pnpm run build

# Python 后端打包
pnpm run build:python

# Windows Electron 安装包
pnpm run build:win

# 环境诊断
uv run ivo doctor
```

CI 在 GitHub Actions 上执行 Python lint、mypy、pytest，以及前端 typecheck/build。

## 架构

### Electron / Vue 前端

- 入口：`electron/main.ts`
- 预加载：`electron/preload.ts`
- 渲染进程入口：`src/main.ts`
- 页面：`src/pages`
- API 客户端：`src/api`
- 状态管理：`src/stores`

Electron 负责窗口生命周期和 Python 服务启动/停止；Vue 前端通过本地 HTTP API 与 FastAPI 后端通信。

### FastAPI 后端

- 服务入口：`scripts/ivo_server_entry.py`
- FastAPI app：`server/main.py`
- 路由：`server/routers`
- 长任务流水线协调：`server/pipeline_runner.py`

后端负责项目管理、模型服务配置、流水线启动/状态查询、时间线片段读写和导出。

### 流水线阶段

核心流水线仍位于 `src/ivo/pipeline`，由 `PipelineOrchestrator` 或 `run_local_command_preview()` 编排。每个阶段在 `JobStore`（SQLite）中记录状态，支持通过现有产物和 job 状态断点续跑。

阶段顺序：

1. `import` - 将源视频复制到 `.ivoproj/assets/`
2. `audio_extract` - FFmpeg 提取标准化 WAV 到 `assets/extracted_audio.wav`
3. `separation` - 本地 Demucs 或 HTTP API 分离人声/背景音
4. `asr` - faster-whisper 或 HTTP API 转录带时间戳片段
5. `diarization` - pyannote 或 HTTP API 分配说话人 ID（可选）
6. `translation` - HTTP API 或 mock 适配器翻译为中文
7. `tts` - F5-TTS/CosyVoice 或 HTTP API 逐片段合成音频
8. `export` - FFmpeg 混合背景音、配音片段和水印，输出 MP4

### 适配器模式

所有模型集成都实现 `src/ivo/adapters/base.py` 中定义的统一接口：

- `StageAdapter`
- `AdapterContext`
- `AdapterResult`

两种主要后端：

- `LocalCommandAdapter`：用 Jinja2 模板渲染命令，运行本地子进程，读取输出 JSON。
- `HttpStageAdapter`：通过 `httpx` 调用 HTTP API，并使用 JSONPath 映射响应。

### Profile 和本地模型配置

虽然旧 PySide UI 已移除，但本地命令 profile 仍是新方案本地模型流水线的重要组成部分，不要直接删除：

- `examples/local_command_profiles*.json`
- `src/ivo/profile_defaults.py`
- `src/ivo/profile_runtime.py`
- `src/ivo/profile_validation.py`
- `src/ivo/pipeline/local_command_preview.py`

这些文件仍被 `server/pipeline_runner.py`、模型预设和本地适配器运行时使用。

### 项目模型

`DubbingProject`（`src/ivo/core/project.py`）以 `.ivoproj` 目录形式存储：

```text
{project}.ivoproj/
  project.json
  segments.sqlite
  jobs.sqlite
  speakers.json
  settings.json
  assets/
  work/
  renders/
```

### 合规层

`src/ivo/compliance` 强制 AI 配音标注：

- 导出前确认
- 嵌入 AI 配音元数据
- 使用 FFmpeg `drawtext` 添加可见水印

## 项目约定

- 所有 Pydantic 模型使用 v2 API：`model_validate()` / `model_dump_json()`。
- SQLite 存储使用原生 `sqlite3` + `Row` 工厂，不使用 ORM。
- Jinja2 模板必须使用 `SandboxedEnvironment` + `StrictUndefined`。
- `mypy` 配置为 strict，新代码必须通过严格类型检查。
- Ruff 行长为 100，目标 Python 3.10。
- 前端 TypeScript 使用严格类型检查。
- HTTP profile 示例只能使用占位符，禁止写入真实凭据。
- 项目不打包模型权重。依赖模型的功能通过 mock 适配器和 dry-run profile 测试。
- 不要提交 `models/`、`runs/`、`.ivoproj/`、媒体文件、密钥或本地环境目录。
