# 2026-06-06 Full GPU F5 + Diarization + LM Studio 完整视频验收

## 目标

在正式扩大测试前，使用用户本机提供的小体积真实视频完整跑通当前质量优先链路，验证以下能力能够在同一次项目运行中协同工作：

- Demucs `htdemucs_ft` GPU 人声/背景声分离
- faster-whisper `large-v3` GPU/float16 ASR
- pyannote community-1 本地模型说话人分离
- LM Studio Qwen3.6 35B 本地 HTTP 翻译/润色
- F5-TTS CUDA 本地配音生成
- 背景声混音和 MP4 导出

## 环境

- 主环境：`.venv`
- pyannote 隔离环境：`.venv-pyannote`
- GPU：NVIDIA GeForce RTX 5090
- 主环境 PyTorch：`torch 2.11.0+cu128`，CUDA 可用
- pyannote 环境 PyTorch：`torch 2.11.0+cu128`，CUDA 可用
- LM Studio endpoint：`http://127.0.0.1:1995/v1/models`
- LM Studio 模型：`qwen3.6-35b-a3b-uncensored-hauhaucs-aggressive-q4_k_p`
- 本地模型目录：`F:\GZYproject\Intelligent-Voice-Over\models`

## 输入

用户本机测试视频，未提交仓库。视频长度约 201.64 秒，文件位于本机 `测试视频` 忽略目录中。

## 命令

```powershell
uv run ivo local-preview $src $out `
  --profiles .\examples\local_command_profiles.real_full_gpu_f5_diarization.json `
  --translation-profile .\examples\http_translation_lm_studio_qwen36_35b.example.json `
  --project-name JP-Full-GPU-F5-Diarization-LMStudio-Full `
  --source-language ja `
  --require-readiness `
  --resume-existing `
  --no-watermark
```

其中：

```powershell
$src = "用户本机测试视频路径，位于被 .gitignore 排除的测试视频目录"
$out = "$env:TEMP\ivo_full_gpu_formal_output"
```

## 结果

- readiness：通过
- 端到端耗时：约 701 秒
- 输出视频：

```text
C:\Users\Administrator\AppData\Local\Temp\ivo_full_gpu_formal_output\JP-Full-GPU-F5-Diarization-LMStudio-Full.ivoproj\renders\local-preview.mp4
```

- 输出视频时长：201.642 秒
- 输出视频大小：19,693,223 bytes，约 18.78 MB
- 生成 TTS 片段：56 个 `.wav`

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

## 片段统计

- 项目片段总数：56
- `rendered`：56
- `duration_ok`：56
- `speaker_ambiguous`：1

说话人映射统计：

| Speaker | 片段数 |
|---|---:|
| SPEAKER_00 | 6 |
| SPEAKER_01 | 3 |
| SPEAKER_02 | 19 |
| SPEAKER_03 | 5 |
| SPEAKER_04 | 23 |

pyannote 原始输出统计：

- pyannote diarization 片段：69
- 已映射回 ASR/TTS 项目片段：56

## 抽样结果

为避免在开源仓库中保存过多真实素材内容，这里只保留少量文本抽样，便于确认 ASR 和翻译链路不是空转。

| 片段 | 时间 | Speaker | 状态 | 质量标记 |
|---|---:|---|---|---|
| seg-001 | 250-3670 ms | SPEAKER_02 | rendered | `speaker_ambiguous`, `duration_ok` |
| seg-002 | 3670-10490 ms | SPEAKER_03 | rendered | `duration_ok` |
| seg-003 | 10490-14830 ms | SPEAKER_04 | rendered | `duration_ok` |
| seg-055 | 192900-199040 ms | SPEAKER_04 | rendered | `duration_ok` |
| seg-056 | 199040-201640 ms | SPEAKER_02 | rendered | `duration_ok` |

## 结论

完整 3 分 21 秒真实视频链路已跑通。当前项目已经具备可复现实测的本地 GPU 流程：分离、识别、说话人分离、LM Studio 翻译、F5-TTS 生成、混音导出全部完成。

后续正式大规模测试前，建议继续补强三类能力：

- 质量评估：增加自动化主观评分入口，例如译文自然度、口型/时长贴合度、音色相似度人工评分表。
- 长视频稳定性：继续用 10-20 分钟素材验证断点续跑、显存释放、阶段耗时和失败恢复。
- 多语言覆盖：在韩语、英语素材上复用同一 GPU profile，确认 ASR 语言参数、翻译提示词和 F5 参考音频策略都稳定。
