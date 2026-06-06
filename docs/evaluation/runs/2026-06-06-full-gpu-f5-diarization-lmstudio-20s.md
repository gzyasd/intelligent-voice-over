# 2026-06-06 Full GPU F5 + Diarization + LM Studio 20 秒预演

## 目标

在正式跑完整视频前，验证当前本机可以跑通质量优先的完整链路：

- Demucs `htdemucs_ft` GPU 人声/背景声分离
- faster-whisper large-v3 GPU/float16 ASR
- pyannote community-1 本地模型说话人分离
- LM Studio Qwen3.6 35B 本地翻译/润色
- F5-TTS CUDA 真实配音生成
- 背景声混音和 MP4 导出

## 环境

- 主环境：`.venv`
- pyannote 隔离环境：`.venv-pyannote`
- GPU：NVIDIA GeForce RTX 5090
- 主环境 PyTorch：`torch 2.11.0+cu128`，CUDA 可用
- pyannote 环境 PyTorch：`torch 2.11.0+cu128`，CUDA 可用
- LM Studio models endpoint：`http://127.0.0.1:1995/v1/models`
- LM Studio 模型：`qwen3.6-35b-a3b-uncensored-hauhaucs-aggressive-q4_k_p`

## 输入

从用户提供的小视频截取 20 秒：

```text
F:\GZYproject\Intelligent-Voice-Over\测试视频\如果中日开战日本会变成什么样？日本节目展开讨论 (高清 720P, AVC, 极高音质, WEB)\如果中日开战日本会变成什么样？日本节目展开讨论 (高清 720P, AVC, 极高音质, WEB).mp4
```

临时样片：

```text
C:\Users\Administrator\AppData\Local\Temp\ivo_full_gpu_probe\jp_full_probe_20s.mp4
```

## 命令

```powershell
uv run ivo local-preview C:\Users\Administrator\AppData\Local\Temp\ivo_full_gpu_probe\jp_full_probe_20s.mp4 C:\Users\Administrator\AppData\Local\Temp\ivo_full_gpu_probe\output --profiles .\examples\local_command_profiles.real_full_gpu_f5_diarization.json --translation-profile .\examples\http_translation_lm_studio_qwen36_35b.example.json --project-name JP-Full-GPU-F5-Diarization-LMStudio-20s --source-language ja --require-readiness --resume-existing --no-watermark
```

## 结果

- readiness：通过
- 输出视频：

```text
C:\Users\Administrator\AppData\Local\Temp\ivo_full_gpu_probe\output\JP-Full-GPU-F5-Diarization-LMStudio-20s.ivoproj\renders\local-preview.mp4
```

- 输出视频大小：约 1.95 MB
- 端到端耗时：约 389 秒

## 阶段状态

| 阶段 | 状态 |
|---|---|
| import | completed |
| audio_extract | completed |
| separation | completed |
| asr | completed |
| diarization | completed |
| translation | completed |
| tts | completed |
| export | completed |

## 片段结果

| 片段 | 时间 | Speaker | 原文 | 译文 | 状态 |
|---|---:|---|---|---|---|
| seg-001 | 250-4090 ms | SPEAKER_00 | 戦争が起きると日本はどうなるか教えていただきたいです | 想请您告诉我，战争爆发后日本会怎样。 | rendered |
| seg-002 | 4090-10470 ms | SPEAKER_01 | ミサイルを飛べないという話でいうと結構いいことにならなそうですよね | 如果导弹飞不起来的话，情况似乎还挺严峻的呢。 | rendered |
| seg-003 | 10470-14050 ms | SPEAKER_00 | 台湾有事に巻き込まれるということであれば | 如果卷入台湾有事的话 | rendered |
| seg-004 | 14830-18450 ms | SPEAKER_00 | 一番考えるのはミサイルが飛んでくるということですね | 首先想到的就是导弹飞过来。 | rendered |
| seg-005 | 18450-19990 ms | SPEAKER_00 | おそらくその前に | 可能在此之前 | rendered |

所有片段质量标记均包含 `duration_ok`。

## 说话人分离

pyannote 本地模型输出了 `SPEAKER_00` 和 `SPEAKER_01`，并成功映射回 ASR 片段。pyannote 使用 `.venv-pyannote` 隔离环境运行，避免与 F5-TTS 的 numpy 依赖冲突。

## 结论

正式完整流程前的关键阻塞已解除：

- 主 F5 环境和 pyannote 环境已隔离。
- pyannote community-1 本地目录可离线加载。
- pyannote wrapper 已绕过 Windows torchcodec 音频解码问题，改用 `soundfile` 预加载音频。
- LM Studio Qwen3.6 35B 可以作为本地翻译 profile 使用。
- 20 秒真实视频完整链路已导出 MP4。

下一步可以扩大到 60 秒或直接跑完整 3 分 21 秒小视频。
