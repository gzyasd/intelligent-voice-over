# 本地模型命令 Profile 使用说明

当前项目用 `LocalCommandAdapter` 接入真实本地模型。每个模型脚本只需要遵守统一命令行合约：读取输入路径和模板变量，写出 JSON 结果，流水线就能继续处理。

## 可直接验证的 dry-run profile

`examples/local_command_profiles.real_dry_run.json` 使用三个真实模型接入脚本，但全部带 `--dry-run`：

- `examples/local_commands/demucs_separate.py --dry-run`
- `examples/local_commands/faster_whisper_asr.py --dry-run`
- `examples/local_commands/f5_tts_command.py --dry-run`

它不会下载模型，也不要求安装 `faster-whisper`、`demucs` 或 `f5_tts`，主要用于验证 profile、脚本合约、FFmpeg 导入导出和时间线状态能完整跑通。

```powershell
cd F:\GZYproject\Intelligent-Voice-Over
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_dry_run.json --project-name "Episode 01" --source-language en --target-text "seg-001=嗯，你好。" --no-watermark
```

真实模型耗时较长，建议每次使用固定的 `--project-name`。如果某个阶段失败，修复环境或 profile 后可增加 `--resume-existing` 继续同一个项目；local preview 会优先复用已完成且文件产物存在的 import、audio_extract、separation 阶段：

```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_dry_run.json --project-name "Episode 01" --source-language en --resume-existing --no-watermark
```

输出位置：

```text
.\demo-output\Episode 01.ivoproj\renders\local-preview.mp4
```

## 切换到真实本地模型

从 dry-run 切到真实模型时，核心动作是复制 `examples/local_command_profiles.real_dry_run.json`，然后逐步删除各阶段命令里的 `--dry-run`。

本地命令 profile 建议使用 `{{ python_executable }}` 作为 Python 入口。它会渲染为当前运行 `ivo` 的解释器路径，避免 Windows 上子进程误用系统 Python 而找不到 `.venv` 中的 `demucs`、`faster-whisper` 或 TTS 依赖。

### ASR：faster-whisper

脚本：`examples/local_commands/faster_whisper_asr.py`

真实运行需要：

- 安装 `faster-whisper`
- 准备模型名称或本地模型目录
- 根据显卡情况调整 `--device` 和 `--compute-type`

示例命令片段：

```json
[
  "{{ python_executable }}",
  "examples/local_commands/faster_whisper_asr.py",
  "--audio",
  "{{ audio_path }}",
  "--language",
  "{{ source_language }}",
  "--model",
  "base",
  "--device",
  "cuda",
  "--compute-type",
  "float16",
  "--out",
  "{{ output_json_path }}"
]
```

输出 JSON 合约：

```json
{
  "segments": [
    {
      "id": "seg-001",
      "start_ms": 100,
      "end_ms": 1100,
      "text": "Well, hi.",
      "speaker_id": "speaker-1"
    }
  ]
}
```

### 人声分离：Demucs

脚本：`examples/local_commands/demucs_separate.py`

真实运行需要：

- 安装 `demucs`
- 根据显卡情况调整 `--device`
- 确认音频长度和显存足够

输出 JSON 合约：

```json
{
  "vocals_path": "path/to/vocals.wav",
  "background_path": "path/to/background.wav"
}
```

### 说话人分离：可选本地命令

本地命令 profiles 可以额外提供 `diarization` 阶段。该阶段读取分离后的人声音频，并输出说话人时间范围；流水线会把这些范围映射回 ASR 片段，用于后续翻译、TTS 和时间线编辑。

`examples/local_command_profiles.mock.json` 已包含一个可直接运行的 mock diarization 命令：

```json
{
  "diarization": {
    "id": "mock-diarization",
    "stage": "diarization",
    "command": [
      "{{ python_executable }}",
      "examples/local_commands/mock_diarization.py",
      "--audio",
      "{{ audio_path }}",
      "--out",
      "{{ output_json_path }}"
    ],
    "output_json_path": "{{ project_path }}/mock-diarization.json"
  }
}
```

输出 JSON 合约：

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

### TTS / 音色克隆：F5-TTS 骨架

脚本：`examples/local_commands/f5_tts_command.py`

当前脚本已经提供 dry-run 合约验证，也支持通过 `--engine-command-json` 把本机 F5-TTS、CosyVoice 或其他中文音色克隆推理脚本接进来。它会把外部命令生成的音频规范化为流水线需要的 JSON 合约。

它已经预留这些变量：

- `{{ segment_text }}`：目标语言台词
- `{{ speaker_id }}`：说话人 ID
- `{{ output_audio_path }}`：生成音频输出路径
- `{{ target_duration_ms }}`：目标片段时长
- `{{ style_prompt }}`：情感、语气或风格提示
- `{{ reference_audio_path }}`：优先从同说话人已审核片段切出的参考音频路径；首次预览没有已审核片段时，会用当前片段兜底；没有可用源音频时为空字符串

`--engine-command-json` 是一个 JSON 数组，数组中的每个字符串会用下面的占位符渲染后执行：

- `{text}`：目标语言台词。
- `{speaker}`：说话人 ID。
- `{audio_out}`：外部推理命令应写入的 WAV 路径。
- `{json_out}`：本脚本最终写入的合约 JSON 路径。
- `{reference_audio}`：可选参考音频路径。
- `{reference_text}`：可选参考音频文本。
- `{style_prompt}`：情绪、语气或风格提示。
- `{duration_ms}`：目标片段时长。

示例命令片段：

```json
[
  "{{ python_executable }}",
  "examples/local_commands/f5_tts_command.py",
  "--text",
  "{{ segment_text }}",
  "--speaker",
  "{{ speaker_id }}",
  "--audio-out",
  "{{ output_audio_path }}",
  "--duration-ms",
  "{{ target_duration_ms }}",
  "--style-prompt",
  "{{ style_prompt }}",
  "--reference-audio",
  "{{ reference_audio_path }}",
  "--json-out",
  "{{ output_json_path }}",
  "--engine-command-json",
  "[\"python\", \"path/to/your_tts_infer.py\", \"--text\", \"{text}\", \"--speaker\", \"{speaker}\", \"--out\", \"{audio_out}\"]"
]
```

Windows profile 中直接内嵌 JSON 容易遇到引号转义问题，也可以把外部推理命令写入文件，然后传 `--engine-command-json-file`：

```json
[
  "{{ python_executable }}",
  "examples/local_commands/f5_tts_command.py",
  "--text",
  "{{ segment_text }}",
  "--speaker",
  "{{ speaker_id }}",
  "--audio-out",
  "{{ output_audio_path }}",
  "--duration-ms",
  "{{ target_duration_ms }}",
  "--json-out",
  "{{ output_json_path }}",
  "--engine-command-json-file",
  "examples/engine_commands/f5_tts_engine_command.example.json"
]
```

可复制 `examples/engine_commands/f5_tts_engine_command.example.json` 或 `examples/engine_commands/cosyvoice_engine_command.example.json`，把其中的 `path/to/...` 改成你本机真实推理脚本。

输出 JSON 合约：

```json
{
  "audio_path": "path/to/generated.wav",
  "duration_ms": 1000
}
```

## GPU 与性能 profile

`examples/local_command_profiles.real_gpu_quality.json` 面向最终质量验证：Demucs 使用 `htdemucs_ft` + CUDA，ASR 使用 `faster-whisper-large-v3` + CUDA/float16，TTS 使用 CosyVoice 本地 wrapper。适合 1-3 分钟到更长样片，但需要确认显存、CUDA、PyTorch 与模型许可证。

`examples/local_command_profiles.real_gpu_fast_preview.json` 面向快速预览：人声分离仍用 CPU small 以降低显存占用，ASR 使用 `small` + CUDA/float16，TTS 使用 dry-run 占位。它不代表最终音色质量，适合先检查导入、分离、ASR、翻译、时间线和导出是否能跑通。

`examples/local_command_profiles.real_separation_asr_tts_f5_gpu_small.json` 面向 Windows/RTX 的真实 F5 快速预览：Demucs 使用 `htdemucs` + CUDA，ASR 使用 `faster-whisper small` + CUDA/float16，TTS 使用 F5-TTS + CUDA。该 profile 已在 RTX 5090、`torch 2.11.0+cu128`、`torchaudio 2.11.0+cu128` 环境中通过授权日语真实样片 20 秒和 1 分钟验收；1 分钟样片耗时约 122 秒，所有阶段完成。

Windows 上新版 `torchaudio` 可能因缺少可用的 `torchcodec` Windows wheel 而无法读写音频。项目的 Demucs adapter 和 F5 adapter 会在真实命令路径中使用 `soundfile` 读写 WAV，从而绕过这条不稳定链路。

CUDA 版 PyTorch 可按需安装：

```powershell
uv pip install --upgrade --index-url https://download.pytorch.org/whl/cu128 torch torchaudio
uv run python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

注意：`uv sync` 可能会把环境恢复到项目锁定的 CPU 稳定组合；每次跑 GPU profile 前都应确认 `torch.cuda.is_available()`。

运行前建议：

```powershell
uv run ivo check-local-readiness .\examples\local_command_profiles.real_gpu_quality.json --models-dir .\models
uv run ivo check-local-readiness .\examples\local_command_profiles.real_gpu_fast_preview.json --models-dir .\models
```

如果 readiness 提示未检测到 NVIDIA 工具，优先改用 `examples/local_command_profiles.real_separation_asr_tts_f5_cpu_small.json` 或 `examples/local_command_profiles.real_separation_asr_tts_cosyvoice_cpu_small.json`。

## 混合线上人声分离 API

如果只想让人声分离阶段走线上模型 API，同时 ASR、说话人分离、翻译、TTS 走本地命令或 mock 覆盖，可以搭配 `examples/http_separation_profile.example.json`：
```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.mock.json --separation-profile .\examples\http_separation_profile.example.json --separation-var api_key=YOUR_API_KEY --project-name "Episode 01" --source-language en
```

人声分离 HTTP profile 可使用 `{{ audio_path }}`、`{{ vocals_path }}` 和 `{{ background_path }}`。响应映射可以返回 `vocals_base64` / `background_base64`，客户端会写入项目 `work/` 目录；也可以返回本地可读的 `vocals_path` / `background_path`。示例 profile 已把 base64 和 path 两组字段都放进 `optional_response_keys`，适配器会分别检查人声和背景音至少各有一种可用输出。

## 混合线上 ASR API

如果只想让 ASR / 转写阶段走线上模型 API，同时分离、翻译、TTS 走本地命令或 mock 覆盖，可以搭配 `examples/http_asr_profile.example.json`：
```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.mock.json --asr-profile .\examples\http_asr_profile.example.json --asr-var api_key=YOUR_API_KEY --project-name "Episode 01" --source-language en
```

ASR HTTP profile 可使用这些模板变量：

- `{{ audio_path }}`：分离后的人声音频路径。
- `{{ source_language }}`：源语言，例如 `en`、`ja`、`ko`。

响应映射必须提供 `segments`，每个片段建议包含 `id`、`start_ms`、`end_ms`、`text` 或 `source_text`、`speaker_id`。字段格式与本地 ASR 命令输出保持一致。

## 混合线上说话人分离 API

如果只想让说话人分离阶段走线上模型 API，同时分离、ASR、翻译、TTS 走本地命令或 mock 覆盖，可以搭配 `examples/http_diarization_profile.example.json`：
```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.mock.json --diarization-profile .\examples\http_diarization_profile.example.json --diarization-var api_key=YOUR_API_KEY --project-name "Episode 01" --source-language en
```

说话人分离 HTTP profile 可使用 `{{ audio_path }}`，响应映射必须提供 `segments`。每个片段需要包含 `start_ms`、`end_ms` 和 `speaker_id`。

## 混合线上翻译 API

如果只想让翻译阶段走线上模型 API，同时 ASR、分离、TTS 走本地命令，可以搭配 `examples/http_translation_profile.example.json`：

```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_dry_run.json --translation-profile .\examples\http_translation_profile.example.json --translation-var api_key=YOUR_API_KEY --project-name "Episode 01" --source-language en
```

`--translation-var` 会进入 HTTP profile 模板上下文，例如：

```json
{
  "Authorization": "Bearer {{ api_key }}"
}
```

## 混合线上 TTS API

如果只想让 TTS / 音色克隆阶段走线上模型 API，同时 ASR、分离、翻译走本地命令或 mock 覆盖，可以搭配 `examples/http_tts_profile.example.json`：

```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.mock.json --tts-profile .\examples\http_tts_profile.example.json --tts-var api_key=YOUR_API_KEY --project-name "Episode 01" --source-language en
```

TTS HTTP profile 可使用这些模板变量：

- `{{ segment_text }}`：要合成的中文台词
- `{{ speaker_id }}`：说话人 ID
- `{{ style_prompt }}`：情绪、语气或风格提示
- `{{ reference_audio_path }}`：本地参考 WAV 路径。若线上服务运行在同一台机器，可以直接读取；若需要上传文件，请在自定义 HTTP profile 中结合 `file_upload_fields` 改造成 multipart 请求
- `{{ target_duration_ms }}`：目标片段时长
- `{{ output_audio_path }}`：期望写入的本地音频路径

响应映射支持两种音频返回方式：

- `audio_base64`：推荐方式，服务端直接返回 base64 编码音频，客户端写入 `work/generated_segments/`。
- `audio_path`：服务端返回本机可读音频路径，客户端复制到目标片段音频路径。

示例 profile 同时映射了 `audio_base64` 和 `audio_path`，并把二者都放进 `optional_response_keys`；适配器会在最终写入音频前检查至少存在一种。

无论哪种方式，都建议返回 `duration_ms`，用于后续时长质量标记。若服务暂时只返回音频，可以把 `duration_ms` 放进 `optional_response_keys`；客户端会用片段目标时长作为兜底值。

## 环境检查

```powershell
uv run ivo doctor
uv run ivo doctor-models
```

`doctor-models` 会报告 `faster-whisper`、`demucs`、`f5_tts` 是否已安装。缺失并不影响 dry-run profile，但会影响去掉 `--dry-run` 后的真实模型运行。

## 翻译到 TTS 的风格提示传递

线上翻译 profile 可以在 `response_mapping` 里额外映射 `style_prompt`：

```json
{
  "response_mapping": {
    "target_text": "$.target_text",
    "emotion": "$.emotion",
    "style_prompt": "$.style_prompt"
  },
  "optional_response_keys": ["style_prompt"]
}
```

`style_prompt` 会进入时间线片段，并在后续本地 TTS 命令或 HTTP TTS profile 中通过 `{{ style_prompt }}` 传给模型。把 `style_prompt` 放进 `optional_response_keys` 后，翻译服务暂时只返回 `emotion` 也不会失败；流水线会自动把 `emotion` 作为 `style_prompt` 的兜底值，保证“温柔、紧张、克制、哭腔”等情绪信息不会在翻译和配音之间丢失。
