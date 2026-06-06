# 本地模型清单与推荐组合

更新时间：2026-06-06

本文记录当前已经下载到本机的模型、它们在 Intelligent Voice Over 项目中的作用，以及面向当前电脑配置和目标效果的推荐模型组合。

当前电脑配置：

- GPU：NVIDIA GeForce RTX 5090，约 32GB 显存
- CPU：Intel Core i7-13700K，16 核 / 24 线程
- 内存：约 32GB
- 模型目录：`F:\GZYproject\Intelligent-Voice-Over\models`

`models/` 已在 `.gitignore` 中排除，不应提交到 GitHub。模型许可证、API key、HF token、测试视频和生成结果也都不应提交。

## 当前已下载模型

| 阶段 | 模型 | 本地目录 | 文件数 | 大小 | 当前状态 |
|---|---|---:|---:|---:|---|
| ASR 语音识别 | `Systran/faster-whisper-tiny` | `models/asr/faster-whisper-tiny` | 13 | 0.07 GB | 已下载 |
| ASR 语音识别 | `Systran/faster-whisper-small` | `models/asr/faster-whisper-small` | 13 | 0.45 GB | 已下载 |
| ASR 语音识别 | `Systran/faster-whisper-large-v3` | `models/asr/faster-whisper-large-v3` | 15 | 2.88 GB | 已下载 |
| ASR 语音识别 | `openai/whisper-large-v3-turbo` | `models/asr/whisper-large-v3-turbo` | 27 | 1.51 GB | 已下载 |
| 人声/背景声分离 | Demucs checkpoints | `models/separation/demucs` | 5 | 0.39 GB | 已下载 |
| 说话人分离 | `pyannote/speaker-diarization-community-1` | `models/diarization/pyannote-community-1` | 21 | 0.03 GB | 已下载 |
| TTS / 音色克隆 | `SWivid/F5-TTS` | `models/tts/F5-TTS` | 19 | 6.28 GB | 已下载 |
| 声码器 | `charactr/vocos-mel-24khz` | `models/tts/vocos-mel-24khz` | 9 | 0.05 GB | 已下载 |
| TTS / 音色克隆 | `FunAudioLLM/Fun-CosyVoice3-0.5B-2512` | `models/tts/Fun-CosyVoice3-0.5B` | 41 | 9.08 GB | 已下载 |
| 本地翻译 / 润色 | `Qwen/Qwen3-8B` | `models/llm/Qwen3-8B` | 31 | 15.27 GB | 已下载 |
| 本地翻译 / 润色 | LM Studio `qwen3.6-35b-a3b-uncensored-hauhaucs-aggressive-q4_k_p` | LM Studio 模型目录 | 由 LM Studio 管理 | 由 LM Studio 管理 | 已安装并可通过 `http://127.0.0.1:1995/v1/models` 发现 |

## 各模型在项目中的作用

### Demucs

作用：从原视频音频中分离人声和背景声。

在项目中的位置：

1. 输入原始视频音频。
2. 输出 `vocals.wav` 和 `no_vocals.wav`。
3. 后续用新配音替换原人声，再与背景音乐、环境声重新混音。

推荐用法：

- 快速预览：`htdemucs`
- 高质量输出：`htdemucs_ft`
- 当前电脑优先使用 CUDA/GPU。

注意事项：

- 影视剧中背景音乐、环境音、笑声和对白经常混在一起，人声分离质量会直接影响最终成片自然度。
- Windows 上音频读写可能受 `torchcodec` / `torchaudio` 影响，项目当前适配中优先使用 `soundfile` 绕过不稳定链路。

### faster-whisper / Whisper

作用：把原视频中的英文、日文、韩文等语音转写成带时间戳的文本片段。

模型分工：

- `faster-whisper-tiny`：极快，适合 CLI、UI、profile 调试。
- `faster-whisper-small`：速度和效果平衡，适合短样片快速验证。
- `faster-whisper-large-v3`：正式质量优先方案，适合最终转写。
- `whisper-large-v3-turbo`：速度优先的大模型方案，适合长视频快速预处理。

推荐用法：

- 开发调试：`small` 或 `tiny`
- 正式输出：`faster-whisper-large-v3` + `cuda` + `float16`
- 长视频快速模式：`whisper-large-v3-turbo`

### pyannote community-1

作用：判断“谁在什么时候说话”，为多角色电视剧配音提供说话人分段。

在项目中的位置：

1. 输入原视频音频或分离后的人声。
2. 输出多个说话人时间段，例如 `SPEAKER_00`、`SPEAKER_01`。
3. 项目把 ASR 文本片段和说话人时间段对齐，后续为不同角色选择不同参考音频和音色。

推荐用法：

- 本地离线方案：`pyannote/speaker-diarization-community-1`
- 线上高质量方案：pyannoteAI `Precision-2`

注意事项：

- Community-1 适合本地离线、自托管、开源项目迭代。
- pyannote 官方说明 `Precision-2` 比 Community-1 更准确，但它是线上 / 商业 API 路线。
- 当前模型文件已下载。由于 Community-1 需要 `pyannote.audio 4.x`，而 F5-TTS 依赖的 numpy 版本与 pyannote 4.x 冲突，正式 F5 + pyannote 流程使用独立 `.venv-pyannote` 环境运行说话人分离。

### F5-TTS

作用：根据参考音频和目标语言文本生成配音，尽量保持原说话人的音色、语气和情绪。

在项目中的位置：

1. 输入参考音频片段、参考文本和翻译后的目标文本。
2. 输出目标语言 WAV。
3. 项目再做时长对齐、混音和视频封装。

推荐用法：

- 当前主线真实 TTS：F5-TTS + CUDA
- 已在本机 RTX 5090 环境跑通过 20 秒、1 分钟日语真实视频样片，以及 3 分 21 秒 Full GPU + pyannote + LM Studio 完整链路。

注意事项：

- F5-TTS 很适合先作为音色克隆主线。
- 常用预训练权重存在非商业限制，商业用途前必须重新确认许可证，或换用许可合适的模型 / 服务。

### vocos-mel-24khz

作用：声码器，把声学特征转换为真实音频波形。

在项目中的位置：

- 作为 F5-TTS 生成链路的一部分。
- 用户通常不直接操作它，但缺少时可能导致 F5-TTS 推理失败或需要在线拉取。

### Fun-CosyVoice3-0.5B

作用：另一条 TTS / zero-shot 音色克隆路线，可作为 F5-TTS 的对比和备用方案。

在项目中的位置：

1. 输入目标文本、参考音频和提示文本。
2. 输出目标语言语音。
3. 适合与 F5-TTS 做同句台词 A/B 测试。

推荐用法：

- 后续优先补齐真实 CosyVoice wrapper 和 engine command。
- 与 F5-TTS 对比自然度、情绪稳定性、跨语言音色保持和许可证适配。

注意事项：

- 模型文件已下载。
- 当前 `doctor-models` 仍提示 `cosyvoice` Python 包缺失，需要按 FunAudioLLM/CosyVoice 官方安装方式补运行环境。

### Qwen3-8B

作用：本地翻译、口语化改写和角色语气润色。

在项目中的位置：

1. 输入 ASR 片段、上下文、角色信息和目标语言。
2. 输出更适合配音的目标语言台词。
3. 控制台词长度，尽量贴近原视频时间轴。

推荐用法：

- 当前本地基础方案：`Qwen3-8B`
- 建议通过 vLLM、SGLang 或其他 OpenAI-compatible HTTP server 接入项目。

注意事项：

- `Qwen3-8B` 足够做本地基础翻译和调试。
- 对影视对白最终质量来说，8B 不是上限；当前 RTX 5090 可以继续评估更大的 Qwen 模型或高质量线上翻译 API。

### LM Studio Qwen3.6 35B A3B

作用：作为当前质量优先的本地 LLM 翻译 / 润色模型。

在项目中的位置：

1. LM Studio 在本机启动 OpenAI-compatible HTTP 服务。
2. 项目通过 `examples/http_translation_lm_studio_qwen36_35b.example.json` 调用 `http://127.0.0.1:1995/v1/chat/completions`。
3. 模型返回 `target_text`、`emotion`、`style_prompt` 三个字段，供后续 TTS 和时间轴使用。

推荐用法：

- 当前质量优先本地翻译：`qwen3.6-35b-a3b-uncensored-hauhaucs-aggressive-q4_k_p`
- 快速调试仍可保留 `Qwen3-8B` 或更小模型。

注意事项：

- LM Studio 的 `/v1/models` 返回的实际模型 ID 是小写，profile 必须使用精确 ID。
- LM Studio 当前结构化输出使用 `response_format.type=json_schema`，不是 `json_object`。
- 该模型是 uncensored / aggressive 社区版本，适合本地探索和影视对白风格测试；正式发布或商业使用前仍需要确认模型来源和许可证。

## 最推荐的一组模型

这里分成三组：快速开发、本地高质量、最终质量优先。原因是“速度、离线、许可证、最终自然度”之间存在取舍。

### A. 快速开发 / 可跑通优先

适合：改代码、调 profile、跑 20 秒样片、验证 UI 和流水线。

| 阶段 | 推荐模型 |
|---|---|
| 人声分离 | Demucs `htdemucs` |
| ASR | `faster-whisper-small` 或 `whisper-large-v3-turbo` |
| 说话人分离 | 暂时可跳过，或用 `pyannote community-1` 短片段 |
| 翻译 | LM Studio Qwen3.6 35B，或 `Qwen3-8B` 快速调试 |
| TTS | F5-TTS GPU |
| 声码器 | `vocos-mel-24khz` |

结论：这是当前最适合持续开发的组合。速度够快，也能覆盖真实模型链路。

### B. 本地高质量 / 当前电脑推荐主线

适合：1-3 分钟样片、正式质量评估、尽量本地离线。

| 阶段 | 推荐模型 |
|---|---|
| 人声分离 | Demucs `htdemucs_ft` + CUDA |
| ASR | `faster-whisper-large-v3` + CUDA + `float16` |
| 说话人分离 | `pyannote/speaker-diarization-community-1` |
| 翻译 | LM Studio `qwen3.6-35b-a3b-uncensored-hauhaucs-aggressive-q4_k_p`，fallback 为 `Qwen3-8B` |
| TTS | F5-TTS GPU 作为当前主线，CosyVoice3 作为优先对比路线 |
| 混音 | 保留 Demucs 背景声，按片段响度和时长重采样/混音 |

结论：这是当前最推荐先落地的一组。它能利用 RTX 5090，且模型大多已经下载完成。

### C. 最终效果优先 / 线上 + 本地混合推荐

适合：追求美剧、日剧、韩剧多角色配音的最终自然度。

| 阶段 | 推荐模型或服务 |
|---|---|
| 人声分离 | Demucs `htdemucs_ft`，必要时评估 UVR / MDX-Net 路线 |
| ASR | `faster-whisper-large-v3`，长视频可用 `whisper-large-v3-turbo` 加速 |
| 说话人分离 | pyannoteAI `Precision-2`，本地 fallback 为 Community-1 |
| 翻译 | 高质量线上 LLM API 或本地更大 Qwen 模型 |
| TTS | F5-TTS、CosyVoice3、以及自定义线上 TTS API 做 A/B 测试 |
| 质量控制 | 自动评估 ASR 置信度、说话人漂移、TTS 时长偏差、音量峰值和静音间隔 |

结论：如果只看最终自然度，这组上限最高；如果要求完全本地离线，则退回 B 组。

## 当前还需要补齐的内容

| 项目 | 当前情况 | 建议 |
|---|---|---|
| `pyannote.audio` 运行包 | 模型已下载，`.venv-pyannote` 隔离环境已在本机验证可导入并可加载本地模型 | 正式流程使用 `examples/local_command_profiles.real_full_gpu_f5_diarization.json` |
| CosyVoice 运行环境 | 模型已下载，Python 包仍缺失 | 按官方仓库安装，接入 engine command |
| 本地 LLM 服务 | LM Studio 已提供 `http://127.0.0.1:1995`，Qwen3.6 35B 模型可发现 | 使用 `examples/http_translation_lm_studio_qwen36_35b.example.json` 作为质量优先翻译 profile |
| 更大翻译模型 | 已有 LM Studio Qwen3.6 35B 量化模型 | 后续主要做真实台词 A/B 质量评估，而不是继续盲目下载 |
| TTS A/B 测试 | F5-TTS 已真实跑通，CosyVoice3 待验证 | 用同一批台词比较音色、情绪、自然度和许可证 |
| 许可证策略 | F5-TTS 预训练权重需谨慎 | 开源发布文档继续保留许可证提醒，商业用途另选模型或 API |

## 推荐优先级

1. 保持当前 F5-TTS GPU 主线，继续跑真实视频样片。
2. 安装并验证 `pyannote.audio`，把说话人分离稳定接入时间线。
3. 补齐 CosyVoice3 真实运行环境，和 F5-TTS 做 A/B 测试。
4. 使用 LM Studio Qwen3.6 35B profile 替代 mock / 外部翻译。
5. 保留 `Qwen3-8B` 作为轻量 fallback，并对真实台词做 A/B 质量评估。
6. 对 20 秒、1 分钟、3 分钟、整集逐级建立验收记录。

## 参考链接

- faster-whisper large-v3：<https://huggingface.co/Systran/faster-whisper-large-v3>
- Whisper large-v3 turbo：<https://huggingface.co/openai/whisper-large-v3-turbo>
- Demucs：<https://github.com/facebookresearch/demucs>
- pyannote community-1：<https://huggingface.co/pyannote/speaker-diarization-community-1>
- pyannote 模型对比：<https://www.pyannote.ai/md/models>
- F5-TTS：<https://huggingface.co/SWivid/F5-TTS>
- Vocos：<https://huggingface.co/charactr/vocos-mel-24khz>
- Fun-CosyVoice3：<https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512>
- Qwen3-8B：<https://huggingface.co/Qwen/Qwen3-8B>
