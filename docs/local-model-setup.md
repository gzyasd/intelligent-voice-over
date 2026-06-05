# 本地模型环境与下载说明

本文档说明真实本地模型的推荐放置方式、下载渠道、许可证注意事项和最小验证命令。项目代码开源，但模型权重、影视素材、API key 和 Hugging Face token 都不应提交到 Git 仓库。

## 基本原则

- 模型权重不进入 Git。默认使用 `models/` 作为本机缓存目录，该目录已被 `.gitignore` 忽略。
- 真实影视素材不进入 Git。测试美剧、日剧、韩剧片段时只使用你拥有授权的本地文件。
- API key、Hugging Face token、ModelScope token 不写进 JSON profile、文档或源码。
- 先跑 `uv run ivo doctor` 和 `uv run ivo doctor-models`，确认 FFmpeg、GPU 工具、Python 包和模型目录状态。
- 优先用 1-3 分钟授权样片验证，再扩大到整集。

## 推荐目录

```text
models/
  asr/
    faster-whisper-large-v3/
    whisper-large-v3-turbo/
  separation/
    demucs/
  diarization/
    pyannote-community-1/
  tts/
    Fun-CosyVoice3-0.5B/
    CosyVoice2-0.5B/
    F5-TTS/
  llm/
    Qwen3-8B/
sample_media/
scratch/
```

`sample_media/` 和 `scratch/` 可用于本机验证，但不要提交真实视频、音频或模型权重。

## 环境检查

```powershell
uv run ivo doctor
uv run ivo doctor-models
uv run ivo doctor-models --models-dir .\models
uv run ivo doctor-models --models-dir .\models --json
uv run ivo doctor-models --models-dir .\models --stage tts
uv run ivo model setup-plan --models-dir .\models
uv run ivo model setup-plan --models-dir .\models --stage tts
uv run ivo model write-setup-script --models-dir .\models --output .\scripts\setup-local-models.ps1
uv run ivo model write-setup-script --models-dir .\models --stage tts --output .\scripts\setup-tts-models.ps1
uv run ivo model smoke-asr --output .\scratch\asr-smoke.json --dry-run
uv run ivo model smoke-adapters --output .\scratch\adapter-smoke.json
```

`doctor-models` 会检查以下信息：

- 阶段：ASR、人声分离、说话人分离、翻译、TTS。
- Python 包是否可导入。
- 推荐安装命令。
- 推荐模型目录是否存在。
- 下载命令或下载渠道。
- 许可证和 token 注意事项。
- 需要 token 的模型会显示环境变量是否已设置，例如 `HF_TOKEN`。
- 最小验证命令。

`uv run ivo doctor-models --json` 适合脚本或 UI 读取结构化诊断结果。`uv run ivo validate-local-profiles .\examples\local_command_profiles.real_dry_run.json --json` 会静态检查 profile 的阶段和关键占位符；`uv run ivo check-local-readiness .\examples\local_command_profiles.real_tts_cosyvoice.json --models-dir .\models --json` 会结合当前模型目录、Python 包和环境变量判断真实 profile 是否具备运行条件。`uv run ivo model setup-plan` 会按阶段输出安装、下载、许可证和验证命令；可以用 `--stage asr`、`--stage separation`、`--stage diarization`、`--stage translation` 或 `--stage tts` 缩小范围。`uv run ivo model write-setup-script` 会把同一批推荐步骤写成 PowerShell 脚本；脚本仍需要你在运行前确认许可证、登录 Hugging Face 或配置必要 token。`uv run ivo model smoke-asr --dry-run` 会生成一段临时 WAV 并验证 ASR adapter JSON 合约；不传 `--output` 时结果写入系统临时目录。去掉 `--dry-run` 后会用 `faster-whisper` 的 tiny/CPU/int8 默认配置做真实最小探测，第一次可能会下载 tiny checkpoint。`uv run ivo model smoke-adapters` 会在不加载真实模型权重的情况下验证 Demucs、faster-whisper、F5-TTS、CosyVoice 本地命令脚本的 dry-run JSON 合约，适合改 profile 或脚本后快速排查。

## 推荐下载命令

### ASR

```powershell
huggingface-cli download Systran/faster-whisper-large-v3 --local-dir .\models\asr\faster-whisper-large-v3
huggingface-cli download openai/whisper-large-v3-turbo --local-dir .\models\asr\whisper-large-v3-turbo
```

### 人声分离

Demucs 通常会在首次运行时下载命名 checkpoint。先安装包，再运行 dry-run 和真实样片验证：

```powershell
uv sync --extra local-separation
uv run python examples/local_commands/demucs_separate.py --help
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_separation_asr_cpu_small.json --project-name "CPU Small Probe" --source-language ja --no-watermark
```

Windows 真实验证中，`demucs==4.0.1` 搭配最新 `torch/torchaudio` 可能在保存 WAV 时遇到 `torchcodec` 或音频 backend 问题；当前项目的 `local-separation` extra 固定为 `torch==2.5.1`、`torchaudio==2.5.1` 并安装 `soundfile`，这是已用 20 秒日语真实样片跑通过的组合。`real_separation_asr_cpu_small` profile 使用 CPU Demucs 和 `faster-whisper small`，适合首次真实验收；高质量整片再切回 `real_separation_asr` 的 large-v3/GPU 配置。

### 说话人分离

pyannote 模型通常需要登录 Hugging Face 并接受模型条件：

```powershell
huggingface-cli login
huggingface-cli download pyannote/speaker-diarization-community-1 --local-dir .\models\diarization\pyannote-community-1
```

不要把 `HF_TOKEN` 写入仓库。需要临时使用时放在当前终端环境变量中：

```powershell
$env:HF_TOKEN="你的 token"
```

### 中文 TTS / 音色克隆

首选先评估 Fun-CosyVoice3：

```powershell
huggingface-cli download FunAudioLLM/Fun-CosyVoice3-0.5B-2512 --local-dir .\models\tts\Fun-CosyVoice3-0.5B
```

国内网络可以用 ModelScope：

```python
from modelscope import snapshot_download

snapshot_download(
    "FunAudioLLM/Fun-CosyVoice3-0.5B-2512",
    local_dir="models/tts/Fun-CosyVoice3-0.5B",
)
snapshot_download("iic/CosyVoice2-0.5B", local_dir="models/tts/CosyVoice2-0.5B")
```

F5-TTS 可作为音色克隆备选：

```powershell
huggingface-cli download SWivid/F5-TTS --local-dir .\models\tts\F5-TTS
```

注意：F5-TTS 代码是 MIT，但预训练模型是 CC-BY-NC，商业用途需要格外谨慎。

### 本地翻译

P0 可以先用线上或本地 OpenAI-compatible HTTP API。需要纯本地时，建议用 Qwen3：

```powershell
huggingface-cli download Qwen/Qwen3-8B --local-dir .\models\llm\Qwen3-8B
```

推荐先通过 vLLM、SGLang 或其他本地服务启动 OpenAI-compatible 接口，再用项目的 HTTP translation profile 接入。

## 最小验证顺序

1. `uv run ivo doctor`
2. `uv run ivo doctor-models --models-dir .\models`
3. `uv run ivo local-preview .\sample_media\en_1min.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_dry_run.json --project-name "Dry Run" --source-language en --no-watermark`
4. 替换 ASR 为真实 faster-whisper profile。
5. 替换人声分离为真实 Demucs profile。
6. 替换 TTS 为真实 CosyVoice 或 F5-TTS profile。
7. 用 1-3 分钟授权样片检查最终视频、背景音、中文配音和元数据。

## 许可证检查清单

- [ ] 当前模型是否允许你的用途。
- [ ] 是否允许商用。
- [ ] 是否要求署名。
- [ ] 是否限制生成内容用途。
- [ ] 是否禁止再分发权重。
- [ ] 是否需要用户接受模型条款。
- [ ] 是否需要 token，且 token 没有进入 Git。

如果许可证不清楚，先不要把该模型写成默认推荐；把它放到“备选评估”里。
