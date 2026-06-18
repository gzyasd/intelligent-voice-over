# 智能视频配音 (Intelligent Voice Over)

> 本地优先的 Windows 桌面端 AI 视频配音工具 —— 将英文 / 日文 / 韩文视频对白重新配成自然的中文音频。

![Python](https://img.shields.io/badge/python-3.10-blue)
![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-orange)
![Platform](https://img.shields.io/badge/platform-Windows-blue)
![UI](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt%206-green)

[English](./README_EN.md) | **中文**

---

## 为什么选择 IVO

- **本地优先**：核心流水线在本地运行，模型权重不上传云端，你的视频素材不离开电脑。
- **双模式接入**：既支持本地模型（Demucs / faster-whisper / pyannote / F5-TTS / CosyVoice），也支持云端 API（OpenAI / Deepgram / ElevenLabs / 阿里云 / 讯飞 等）。
- **可视化桌面端**：PySide6 单窗口应用，从项目创建到时间线审片全流程可视化操作，无需命令行。
- **断点续跑**：每个阶段独立记录状态，中途失败后修复环境即可从断点继续，不浪费已完成的产物。
- **合规内置**：导出时自动嵌入 AI 配音元数据，支持可见水印，确保 AI 生成内容透明标注。
- **批量处理**：支持整季剧集批量跑，单集失败不影响后续，最终汇总报告。

## 流水线

```
源视频
  │
  ├─ 1. 导入          复制源视频到项目
  ├─ 2. 音频提取      FFmpeg 提取标准化 WAV
  ├─ 3. 人声分离      Demucs / HTTP API → vocals.wav + background.wav
  ├─ 4. 语音转写      faster-whisper / HTTP API → 带时间戳的片段
  ├─ 5. 说话人分离    pyannote / HTTP API（可选）→ 分配说话人 ID
  ├─ 6. 文本翻译      LM Studio / HTTP API → 中文文本
  ├─ 7. 语音合成      F5-TTS / CosyVoice / HTTP API → 逐片段中文音频
  └─ 8. 混合导出      FFmpeg 混合背景音 + 对齐片段 + 水印 → 最终 MP4
```

每个阶段独立记录状态，支持 `--resume-existing` 断点续跑。

## 快速开始

### 前置要求

- Windows 10/11
- Python 3.10
- [uv](https://docs.astral.sh/uv/) 包管理器

> FFmpeg 已内置在仓库的 `ffmpeg/bin/` 目录中，克隆后即可使用，无需单独安装或配置环境变量。

### 安装

```powershell
git clone <repo-url>
cd Intelligent-Voice-Over
uv sync --dev
```

### 环境诊断

```powershell
uv run ivo doctor
```

### 启动桌面 UI

```powershell
uv run python -m ivo.app
```

### 生成测试样片（不含真实素材）

```powershell
uv run python .\scripts\create_sample_media.py --output-dir .\sample_media
```

### FFmpeg 说明

仓库已内置 FFmpeg 8.0.1 essentials build（位于 `ffmpeg/bin/`），覆盖音频提取、视频混合导出等全部流水线需求。程序会按以下优先级查找 FFmpeg：

1. 项目内置的 `ffmpeg/bin/`（默认，开箱即用）
2. `IVO_FFMPEG_PATH` 环境变量（完整路径）
3. `IVO_FFMPEG_DIR` 环境变量（目录）
4. 系统 PATH

如需替换为其他 FFmpeg 版本，直接覆盖 `ffmpeg/bin/` 下的文件即可。打包便携版时也会自动包含此目录。

## 桌面端使用

桌面端采用左侧导航布局：

| 页面 | 用途 |
|------|------|
| **首页** | 快速入口和最近项目 |
| **项目库** | 管理所有 `.ivoproj` 项目，支持打开、查看文件夹、删除 |
| **当前项目** | 生成进度、时间线审片、单句重生成、最终导出 |
| **模型中心** | 选择模型目录、一键检查就绪状态、管理模型方案 |
| **模型服务** | 配置云端 API 提供商（OpenAI / Deepgram / ElevenLabs 等） |
| **设置** | 项目目录、最近项目等用户偏好 |

推荐工作流：

1. 在「模型中心」选择模型目录并一键检查就绪状态
2. 通过 4 步向导新建项目（选择视频 → 选择语言 → 选择模型方案 → 确认）
3. 在「当前项目 → 生成进度」查看阶段和句子级进度
4. 完成后在「时间线」审片，可单句重生成
5. 确认后执行最终导出（含合规水印）

## CLI 使用

### Mock 预览（不依赖真实模型）

```powershell
uv run ivo mock-preview .\sample.mp4 .\demo-output --project-name "Episode 01" --source-language en
```

### 本地模型预览

```powershell
# CPU 小预览
uv run ivo local-preview .\sample.mp4 ^
  --profiles .\examples\local_command_profiles.real_separation_asr_tts_f5_cpu_small.json ^
  --project-name "Episode 01" --source-language ja ^
  --require-readiness --models-dir .\models --resume-existing --no-watermark

# GPU 完整质量
uv run ivo local-preview .\sample.mp4 ^
  --profiles .\examples\local_command_profiles.real_full_gpu_f5_diarization.json ^
  --translation-profile .\examples\http_translation_lm_studio_qwen36_35b.example.json ^
  --project-name "Full GPU Episode 01" --source-language ja ^
  --require-readiness --models-dir .\models --resume-existing --no-watermark
```

### 批量处理

```powershell
uv run ivo batch-local-preview .\episodes ^
  --profiles .\examples\local_command_profiles.real_dry_run.json ^
  --source-language en --no-watermark ^
  --report .\demo-output\batch-report.json --skip-existing
```

### Profile 校验

```powershell
uv run ivo validate-local-profiles .\examples\local_command_profiles.real_dry_run.json --json
uv run ivo check-local-readiness .\examples\local_command_profiles.real_full_gpu_f5_diarization.json --models-dir .\models --json
```

## 两种接入模式

### 本地模型

项目不打包模型权重。通过模型方案（scheme）配置本地模型：

```powershell
uv run ivo model setup-plan --models-dir .\models
uv run ivo model write-setup-script --models-dir .\models
```

或在桌面端「模型中心」直接选择模型目录并一键检查。

| 阶段 | 推荐模型 | 说明 |
|------|----------|------|
| 人声分离 | Demucs `htdemucs_ft` | GPU 优先 |
| 语音转写 | faster-whisper `large-v3` | GPU/float16 |
| 说话人分离 | pyannote community-1 | 需接受 HF 模型条款 |
| 文本翻译 | LM Studio + Qwen3 | 本地 HTTP 服务 |
| 语音合成 | F5-TTS / CosyVoice | F5 权重为 CC-BY-NC，商用需换权重 |

### 云端 API

通过 `ApiAdapterProfile` 描述 HTTP API，所有阶段均可替换为云端服务：

```powershell
# 添加 HTTP adapter
uv run ivo adapter add-http .\adapters.json ^
  --id translator --stage translation ^
  --url https://api.example.test/translate ^
  --response target_text=$.text

# 使用 HTTP 翻译替换本地翻译
uv run ivo local-preview .\sample.mp4 .\demo-output ^
  --profiles .\examples\local_command_profiles.mock.json ^
  --translation-profile .\examples\http_translation_profile.example.json ^
  --translation-var api_key=YOUR_API_KEY ^
  --project-name "HTTP Translation" --source-language ja
```

内置支持的云端提供商：

| 提供商 | 支持阶段 |
|--------|----------|
| OpenAI | ASR + 说话人分离 + TTS |
| Deepgram | ASR |
| AudioShake | 人声分离 |
| LALAL.AI | 人声分离 |
| 阿里云百炼 | ASR |
| 阿里云 Qwen-TTS | TTS |
| ElevenLabs | TTS |
| Anthropic | 翻译 |
| OpenAI 兼容 | 翻译 |
| 讯飞开放平台 | ASR + 说话人分离 |

## 项目结构

```
{project}.ivoproj/
  project.json       项目元数据
  segments.sqlite    时间线片段存储
  jobs.sqlite        阶段执行状态
  speakers.json      说话人配置
  settings.json      项目设置
  assets/            源视频、提取的音频
  work/              人声、背景音、生成的片段音频
  renders/           最终输出视频
```

## 开发

```powershell
# 运行全部测试
uv run pytest

# 代码检查
uv run ruff check .

# 类型检查（严格模式）
uv run mypy src

# Windows 打包（空运行）
uv run python scripts/build_windows_package.py --dry-run --output-dir dist
```

## 许可证

本项目源码采用 **PolyForm Noncommercial License 1.0.0**。你可以在非商业用途下查看、学习、修改、运行和分发本项目代码，但**未经作者书面授权，不得用于商业用途**。

> PolyForm Noncommercial License 不是 OSI 认证的开源许可证，因为它限制商业使用。本项目采用「源码开放 / 非商业使用许可」的发布方式。

商业使用包括但不限于：付费产品、SaaS 服务、企业内部生产部署、付费交付、商业项目集成、收费部署/咨询/运维。商业授权说明见 [COMMERCIAL-LICENSE.md](./COMMERCIAL-LICENSE.md)。

**第三方模型注意事项**：F5-TTS 代码是 MIT，但默认预训练权重为 CC-BY-NC，商业用途前必须换用许可证合适的模型或服务。第三方模型许可证彼此独立，不会因为本项目代码采用 PolyForm Noncommercial 而自动变成同一许可证。

## 贡献

参与贡献前请阅读：

- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)
- [SECURITY.md](./SECURITY.md)
- [docs/compliance-and-licenses.md](./docs/compliance-and-licenses.md)

请不要向仓库提交真实 API key、token、未授权视频/音频素材或模型权重。

## 更多文档

- [本地模型环境配置](./docs/local-model-setup.md)
- [本地命令 Profile 指南](./docs/local-model-command-profiles.md)
- [HTTP API Profile 指南](./docs/http-api-profiles.md)
- [桌面端使用说明](./docs/ui-local-preview.md)
- [Windows 打包说明](./docs/windows-packaging.md)
- [合规与许可证](./docs/compliance-and-licenses.md)
