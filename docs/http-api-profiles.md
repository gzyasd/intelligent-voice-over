# 自定义线上 API Profile 指南

本项目的线上模型接入通过 `ApiAdapterProfile` 描述。ASR、人声分离、说话人分离、翻译和 TTS 都可以替换为 HTTP API；本地模型和线上 API 共用同一套阶段合约。

不要把 API key、token、真实视频、音频或生成结果写进 profile 或提交到 Git。密钥应通过命令行变量传入，例如 `--translation-var api_key=...`，或由本机环境变量/外部启动脚本管理。

## JSON API

普通 JSON API profile 至少包含以下字段：

```json
{
  "id": "online-translation",
  "stage": "translation",
  "method": "POST",
  "url": "https://api.example.test/translate",
  "headers": {
    "Authorization": "Bearer {{ api_key }}"
  },
  "request_template": {
    "text": "{{ segment_text }}",
    "source_language": "{{ source_language }}",
    "target_language": "{{ target_language }}",
    "speaker_id": "{{ speaker_id }}"
  },
  "response_mapping": {
    "target_text": "$.target_text",
    "style_prompt": "$.style_prompt"
  },
  "optional_response_keys": ["style_prompt"],
  "timeout_seconds": 120
}
```

运行示例：

```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.mock.json --translation-profile .\examples\http_translation_profile.example.json --translation-var api_key=YOUR_API_KEY --project-name "HTTP Translation" --source-language ja
```

## multipart

如果 API 需要上传音频文件，使用 `file_upload_fields`。key 是 multipart 字段名，value 是 adapter 上下文变量名：

```json
{
  "id": "online-asr-upload",
  "stage": "asr",
  "method": "POST",
  "url": "https://api.example.test/asr",
  "headers": {
    "Authorization": "Bearer {{ api_key }}"
  },
  "request_template": {
    "source_language": "{{ source_language }}"
  },
  "file_upload_fields": {
    "audio": "audio_path"
  },
  "response_mapping": {
    "segments": "$.segments"
  },
  "timeout_seconds": 120
}
```

ASR 返回的 `segments` 应与本地 ASR wrapper 一致：

```json
{
  "segments": [
    {
      "id": "seg-001",
      "start_ms": 0,
      "end_ms": 1200,
      "text": "Hello.",
      "speaker_id": "speaker-1"
    }
  ]
}
```

## OpenAI-compatible

本地 vLLM、SGLang 或线上 OpenAI-compatible 服务可使用 `examples/http_translation_openai_compatible.example.json`。运行时传入 `base_url`、`model` 和 `api_key`：

```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.mock.json --translation-profile .\examples\http_translation_openai_compatible.example.json --translation-var base_url=http://127.0.0.1:8000 --translation-var model=Qwen3-8B --translation-var api_key=local-key --project-name "Qwen Translation" --source-language ja
```

如果使用本机 LM Studio，并且服务地址是 `http://127.0.0.1:1995`，可以直接使用项目内置的 Qwen3.6 35B profile：

```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_separation_asr_tts_f5_gpu_small.json --translation-profile .\examples\http_translation_lm_studio_qwen36_35b.example.json --project-name "LM Studio Qwen Translation" --source-language ja --no-watermark
```

正式质量预演可以把它和 GPU + F5 + pyannote profile 搭配：

```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_full_gpu_f5_diarization.json --translation-profile .\examples\http_translation_lm_studio_qwen36_35b.example.json --project-name "Full GPU LM Studio Probe" --source-language ja --require-readiness --resume-existing --no-watermark
```

该 profile 当前固定使用 LM Studio 模型 ID：

```text
qwen3.6-35b-a3b-uncensored-hauhaucs-aggressive-q4_k_p
```

LM Studio 当前接口不要求 API key。项目的 LM Studio profile 使用强提示词要求模型输出 JSON；解析器也兼容模型偶尔返回的 ```json 代码块包装。

翻译 API 建议返回 JSON 字符串，至少包含：

```json
{
  "target_text": "你好。",
  "emotion": "warm",
  "style_prompt": "自然、温和、保留短暂停顿"
}
```

## TTS 返回 audio_base64

TTS API 可以直接返回 `audio_base64`：

```json
{
  "audio_base64": "BASE64_WAV_BYTES",
  "duration_ms": 1200
}
```

对应 mapping：

```json
{
  "response_mapping": {
    "audio_base64": "$.audio_base64",
    "duration_ms": "$.duration_ms"
  },
  "optional_response_keys": ["duration_ms"]
}
```

## TTS 返回 audio_path

如果 API 服务和本项目运行在同一台机器上，也可以返回本地可读的 `audio_path`：

```json
{
  "audio_path": "C:/Temp/tts-output/seg-001.wav",
  "duration_ms": 1200
}
```

对应 mapping：

```json
{
  "response_mapping": {
    "audio_path": "$.audio_path",
    "duration_ms": "$.duration_ms"
  },
  "optional_response_keys": ["duration_ms"]
}
```

## 错误返回

推荐服务端错误格式：

```json
{
  "error": {
    "message": "quota exhausted"
  }
}
```

项目会优先提取 `error.message`、`message` 或字符串型 `error` 作为错误摘要，并保留 HTTP status 和是否可重试。

## 校验命令

```powershell
uv run ivo validate-http-profile .\examples\http_translation_profile.example.json --json
uv run ivo validate-http-profile .\examples\http_asr_profile.example.json --json
uv run ivo validate-http-profile .\examples\http_tts_profile.example.json --json
```
