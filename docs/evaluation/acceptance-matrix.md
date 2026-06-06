# 真实视频配音验收矩阵

本文档用于统一后续真实样片、模型组合、UI 流程和发布流程的验收口径。它不包含任何真实影视素材、音频、模型权重或导出视频，只记录可复现的方法和通过标准。

## 阶段验收矩阵

| 阶段 | P0 预览版标准 | P1 可长期使用标准 | P2 发布版标准 |
| --- | --- | --- | --- |
| 环境检查 | `ivo doctor` 能检测 Python、FFmpeg；`doctor-models` 能区分 installed/missing | UI 中能显示同等 readiness 结果 | 安装包中能给出清晰缺失依赖提示 |
| 人声分离 | 20 秒授权样片可输出 vocals/background | 1-3 分钟样片可稳定输出，支持恢复 | 5-10 分钟样片失败后可定位并重跑 |
| ASR | faster-whisper small/CPU 能生成带时间戳片段 | large-v3/GPU 或 API 模式可用于高质量样片 | 英/日/韩样片都有记录和质量统计 |
| 说话人分离 | 可选阶段，不阻塞单人样片 | 多角色样片能映射 speaker 并标记不确定片段 | UI 可编辑角色、参考片段和音色绑定 |
| 翻译 | 默认直通或 mock 翻译不阻塞预览 | HTTP/OpenAI-compatible 翻译可输出自然中文、emotion、style_prompt | 支持术语表、剧集风格和审核流程 |
| TTS/音色克隆 | F5-TTS 20 秒真实链路可导出 | CosyVoice/F5 至少一条路线可用于 1-3 分钟样片 | 用户能选择本地或线上 TTS profile |
| 混音导出 | 背景音和配音能合成 MP4，写入 AI 配音元数据 | 片段时长、静音、缺参考音频有质量标记 | 最终导出经过确认闸门和可选水印 |
| UI | mock/local preview 基础流程可跑 | UI 可选 profile、检查 readiness、看日志、单句重生成 | 安装包 UI 冒烟通过 |
| 批处理/恢复 | `--resume-existing` 能复用短片段阶段产物 | 目录批处理能生成 report 并跳过已完成项目 | 整集级别任务可失败恢复 |

## 样片分层

| 层级 | 时长 | 人物数 | 用途 | 通过条件 |
| --- | --- | --- | --- | --- |
| Smoke-20s | 20 秒 | 1-2 人 | 验证命令、模型和导出链路 | 完整导出 MP4，所有关键 job completed |
| Probe-90s | 1-3 分钟 | 1-2 人 | 验证真实可看性、恢复和 TTS 耗时 | 可导出或可恢复，失败信息可定位 |
| Review-5m | 5-10 分钟 | 2-4 人 | 验证多角色、质量面板、局部重生成 | 可完成审核和最终导出 |
| Episode | 整集 | 多人 | 验证长期稳定性、批处理和性能 | 可批量处理，失败项目有 report |

所有样片必须是用户拥有授权的本地文件、自制素材或公开可测试素材。仓库不保存原片、切片、音频、TTS 结果或导出视频。

## 模型组合

| 组合 | Profile | 用途 | 当前状态 |
| --- | --- | --- | --- |
| Mock E2E | `examples/local_command_profiles.mock.json` | CI 和 UI 快速验证 | 已可用 |
| Dry Run Real Commands | `examples/local_command_profiles.real_dry_run.json` | 验证本地命令合约 | 已可用 |
| CPU Separation + ASR | `examples/local_command_profiles.real_separation_asr_cpu_small.json` | 快速真实分离/ASR 验收 | 已通过 20 秒真实样片 |
| CPU F5 Full Preview | `examples/local_command_profiles.real_separation_asr_tts_f5_cpu_small.json` | 真实本地 TTS 预览 | 已通过 20 秒和 1 分钟真实样片 |
| GPU F5 Small Preview | `examples/local_command_profiles.real_separation_asr_tts_f5_gpu_small.json` | RTX/CUDA 环境下的真实本地 F5 预览 | 已通过 20 秒和 1 分钟真实样片，1 分钟耗时约 122 秒 |
| Full GPU F5 + Diarization + LM Studio | `examples/local_command_profiles.real_full_gpu_f5_diarization.json` + `examples/http_translation_lm_studio_qwen36_35b.example.json` | 当前质量优先本地链路 | 已通过 20 秒预检和 3 分 21 秒完整真实视频；56 个片段全部 `rendered`，8 个阶段全部 `completed` |
| CosyVoice Full Preview | `examples/local_command_profiles.real_separation_asr_tts_cosyvoice_cpu_small.json` | 下一条优先 TTS 路线 | 待实现和验证 |
| GPU Quality | `examples/local_command_profiles.real_gpu_quality.json` | 高质量本地模式 | profile 已提供；CosyVoice 模型安装后再做质量验收 |
| HTTP Hybrid | HTTP stage override profiles | 线上 API 或本地 OpenAI-compatible 服务 | LM Studio 本地 OpenAI-compatible 翻译已在完整 GPU 链路中通过 |

## 通过条件

P0 通过条件：

- `uv run pytest`、`uv run ruff check .`、`uv run mypy src` 全部通过。
- `uv run ivo doctor` 能检测 FFmpeg。
- `uv run ivo doctor-models` 能输出每个模型阶段的安装、下载、许可证和验证命令。
- 20 秒真实样片可通过至少一条本地模型链路导出 MP4。
- 导出视频包含背景音、中文配音、AI 配音元数据。
- 失败时能指出具体 stage、provider 和错误摘要。

P1 通过条件：

- 1-3 分钟真实样片可完成或可恢复；当前 Full GPU F5 + Diarization + LM Studio 链路已完成 3 分 21 秒真实样片。
- UI 能选择本地/HTTP profile、检查 readiness、查看运行日志。
- 时间线能编辑译文、speaker、style prompt，并可单句重生成。
- 质量面板能统计时长偏差、静音、缺参考音频、speaker 不确定等问题。
- 批处理能输出机器可读 report。

P2 通过条件：

- Windows 打包脚本通过本地冒烟。
- Release 文档明确不包含模型权重和影视素材。
- 合规文档说明模型许可证、素材授权、AI 配音元数据和可见水印。
- 最终验收记录覆盖 mock、20 秒真实样片、1-3 分钟真实样片、完整 GPU + 说话人分离 + 本地 LLM 翻译链路和 UI 冒烟。

## 失败处理

真实模型或 API 失败时，按以下顺序处理：

1. 保留输出目录和项目名，用 `--resume-existing` 复用已完成阶段。
2. 运行 `uv run ivo check-local-readiness <profile> --json` 检查缺包、模型目录、token 和 engine command。
3. 查看 adapter 错误中的 stage、provider、command、exit code、stderr summary 或 HTTP status。
4. 如果是 TTS 单句失败，只重跑失败片段，已 `rendered` 的片段不得重复生成。
5. 如果是许可证、token 或模型下载问题，只更新文档和 readiness 提示，不把 token 或模型权重提交到 Git。
6. 每次真实失败都应写入 `docs/evaluation/runs/` 的运行记录，只记录命令、模型组合、错误摘要和下一步，不记录真实素材路径中的敏感信息。
