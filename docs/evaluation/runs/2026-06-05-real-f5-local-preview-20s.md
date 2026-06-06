# 2026-06-05 F5-TTS 真实本地预览 20 秒验收

## 目标

验证 20 秒真实日语视频片段可以通过本地模型完成完整预览链路：

- Demucs 分离人声/背景音
- faster-whisper small CPU/int8 转写
- F5-TTS 真实生成配音音频
- 背景音与生成配音混音
- 导出带 AI 配音元数据的 MP4

## 环境

- 操作系统：Windows
- Python：3.10.6
- FFmpeg：8.1.1 full build
- 分离：Demucs `htdemucs`，CPU
- ASR：faster-whisper `small`，CPU/int8
- TTS：`f5-tts==1.1.20`，CPU，`F5TTS_v1_Base`
- Transformers：`<5`，避免当前 Torch 组合触发兼容问题

## 使用 profile

```powershell
.\examples\local_command_profiles.real_separation_asr_tts_f5_cpu_small.json
```

该 profile 用于低门槛真实验收，优先保证 CPU 环境可跑通，不代表最终速度和质量上限。

## 验收命令

```powershell
uv run ivo local-preview C:\Users\Administrator\AppData\Local\Temp\ivo_real_probe\jp_probe_20s.mp4 C:\Users\Administrator\AppData\Local\Temp\ivo_real_preview_f5_reftext2 --profiles .\examples\local_command_profiles.real_separation_asr_tts_f5_cpu_small.json --project-name JP-Real-F5-RefText2-20s --source-language ja --require-readiness --no-watermark
```

## 结果

- readiness：通过，分离、ASR、F5-TTS 均可用。
- 生成片段：5 个片段全部生成 WAV。
- 导出视频：成功。
- 输出文件：`C:\Users\Administrator\AppData\Local\Temp\ivo_real_preview_f5_reftext2\JP-Real-F5-RefText2-20s.ivoproj\renders\local-preview.mp4`
- 端到端耗时：约 7 分钟，其中主要耗时来自 CPU 上的 F5-TTS。

## 本轮发现并修复

真实 F5 预览第一次失败时，F5 wrapper 没有收到参考文本，导致官方 CLI 试图自行转写参考音频，并在 Windows 上触发 `torchcodec`/PyTorch/FFmpeg 组合兼容问题。

本轮修复：

- TTS adapter 上下文新增 `reference_text`。
- `synthesize_segment` 使用原始 `segment.source_text` 作为参考文本。
- F5 profile 显式传入 `--reference-text {{ reference_text }}`。
- 新增回归测试，防止本地命令 profile 或 adapter 再次漏传参考文本。

## 限制

- 当前测试使用 CPU，速度较慢。
- 20 秒样片只验证完整链路可运行，不代表长视频稳定性、角色一致性和商业级音色质量已经达标。
- F5-TTS 默认预训练权重为 CC-BY-NC，商业用途前必须换用许可证合适的模型或服务。
