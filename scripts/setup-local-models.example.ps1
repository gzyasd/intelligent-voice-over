$ErrorActionPreference = "Stop"

# Intelligent Voice Over local model setup example.
# 确认模型许可证后再下载或使用；模型许可证不等同于本项目 MIT 代码许可证。
# 不要提交 models/、真实视频、生成音频、API key、HF_TOKEN 或其他密钥到 Git。
# 如需访问 Hugging Face 受限模型，请先运行 huggingface-cli login；不要把 token 写入脚本。

Write-Host "确认模型许可证后再继续。不要提交 models/ 或任何 token。"
New-Item -ItemType Directory -Force -Path ".\models" | Out-Null

# Python extras for local engines.
uv sync --extra local-separation
uv sync --extra local-tts-f5
uv sync --extra local-tts-cosyvoice

# Optional: required for gated Hugging Face models such as pyannote.
huggingface-cli login

# ASR.
huggingface-cli download Systran/faster-whisper-large-v3 --local-dir ".\models\asr\faster-whisper-large-v3"
huggingface-cli download openai/whisper-large-v3-turbo --local-dir ".\models\asr\whisper-large-v3-turbo"

# Diarization. Accept model terms on Hugging Face before downloading.
huggingface-cli download pyannote/speaker-diarization-community-1 --local-dir ".\models\diarization\pyannote-community-1"

# TTS / voice cloning candidates. Confirm each model card license before real use.
huggingface-cli download FunAudioLLM/Fun-CosyVoice3-0.5B-2512 --local-dir ".\models\tts\Fun-CosyVoice3-0.5B"
huggingface-cli download FunAudioLLM/CosyVoice2-0.5B --local-dir ".\models\tts\CosyVoice2-0.5B"
huggingface-cli download SWivid/F5-TTS --local-dir ".\models\tts\F5-TTS"

# Local translation model candidate for OpenAI-compatible serving.
huggingface-cli download Qwen/Qwen3-8B --local-dir ".\models\llm\Qwen3-8B"

# Quick checks after installation.
uv run ivo doctor-models --models-dir ".\models"
uv run ivo model smoke-adapters --output ".\scratch\adapter-smoke.json"
