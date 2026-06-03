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

输出位置：

```text
.\demo-output\Episode 01.ivoproj\renders\local-preview.mp4
```

## 切换到真实本地模型

从 dry-run 切到真实模型时，核心动作是复制 `examples/local_command_profiles.real_dry_run.json`，然后逐步删除各阶段命令里的 `--dry-run`。

### ASR：faster-whisper

脚本：`examples/local_commands/faster_whisper_asr.py`

真实运行需要：

- 安装 `faster-whisper`
- 准备模型名称或本地模型目录
- 根据显卡情况调整 `--device` 和 `--compute-type`

示例命令片段：

```json
[
  "python",
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

### TTS / 音色克隆：F5-TTS 骨架

脚本：`examples/local_commands/f5_tts_command.py`

当前脚本已经提供 dry-run 合约验证，但真实推理部分仍需要按本机 F5-TTS 项目、checkpoint 和参考音频格式补上具体调用。它已经预留这些变量：

- `{{ segment_text }}`：目标语言台词
- `{{ speaker_id }}`：说话人 ID
- `{{ output_audio_path }}`：生成音频输出路径
- `{{ target_duration_ms }}`：目标片段时长
- `{{ style_prompt }}`：情感、语气或风格提示

输出 JSON 合约：

```json
{
  "audio_path": "path/to/generated.wav",
  "duration_ms": 1000
}
```

## 混合线上 ASR API

如果只想让 ASR / 转写阶段走线上模型 API，同时分离、翻译、TTS 走本地命令或 mock 覆盖，可以搭配 `examples/http_asr_profile.example.json`：
```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.mock.json --asr-profile .\examples\http_asr_profile.example.json --asr-var api_key=YOUR_API_KEY --project-name "Episode 01" --source-language en
```

ASR HTTP profile 可使用这些模板变量：

- `{{ audio_path }}`：分离后的人声音频路径。
- `{{ source_language }}`：源语言，例如 `en`、`ja`、`ko`。

响应映射必须提供 `segments`，每个片段建议包含 `id`、`start_ms`、`end_ms`、`text` 或 `source_text`、`speaker_id`。字段格式与本地 ASR 命令输出保持一致。

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
- `{{ target_duration_ms }}`：目标片段时长
- `{{ output_audio_path }}`：期望写入的本地音频路径

响应映射支持两种音频返回方式：

- `audio_base64`：推荐方式，服务端直接返回 base64 编码音频，客户端写入 `work/generated_segments/`。
- `audio_path`：服务端返回本机可读音频路径，客户端复制到目标片段音频路径。

无论哪种方式，都建议返回 `duration_ms`，用于后续时长质量标记。

## 环境检查

```powershell
uv run ivo doctor
uv run ivo doctor-models
```

`doctor-models` 会报告 `faster-whisper`、`demucs`、`f5_tts` 是否已安装。缺失并不影响 dry-run profile，但会影响去掉 `--dry-run` 后的真实模型运行。
