# 智能视频配音

这是一个本地优先的 Windows 桌面端项目，目标是把英文、日文、韩文视频对白重新配成自然的中文配音，并支持本地模型与自定义线上模型 API 两种模式。

当前状态：已完成 v1 的可测试工程骨架、mock 端到端流水线、本地命令 adapter、HTTP adapter、基础桌面 UI、时间线编辑/单句后台重生成、最终导出和导出合规闸门。详细计划见 `docs/superpowers/plans/2026-06-01-intelligent-video-dubbing-v1.md`。

最新真实模型基线：已在本机授权日语样片上跑通 CPU、GPU 和完整质量优先三条本地链路。当前最高质量验收链路使用 Demucs `htdemucs_ft` GPU 分离、faster-whisper `large-v3` GPU/float16 ASR、pyannote community-1 本地说话人分离、LM Studio Qwen3.6 35B 本地翻译，以及 F5-TTS CUDA 真实生成；3 分 21 秒真实视频完整导出耗时约 701 秒，56 个片段全部 `rendered`。当前剩余完整实施计划见 `docs/superpowers/plans/2026-06-05-complete-remaining-implementation-plan.md`，验收矩阵见 `docs/evaluation/acceptance-matrix.md`，最终验收记录见 `docs/evaluation/runs/2026-06-final-acceptance.md`，完整 GPU 跑测记录见 `docs/evaluation/runs/2026-06-06-full-gpu-f5-diarization-lmstudio-full.md`。

默认模型策略：CLI 和桌面 UI 在未手动指定本地命令 profile 时，会优先选择 `examples/local_command_profiles.real_separation_asr_tts_f5_gpu_small.json`；如果未检测到 NVIDIA 工具或 GPU profile 不存在，再回退到 `examples/local_command_profiles.real_separation_asr_tts_f5_cpu_small.json`。手动传入 `--profiles` 或在 UI 里选择 profile 时，会尊重用户选择。

注意：F5-TTS 代码是 MIT，但默认预训练权重为 CC-BY-NC，商业用途前必须换用许可证合适的模型或服务。下一条优先评估的真实 TTS 路线是 CosyVoice。真实视频素材、生成音频/视频、模型权重、API key 和 token 都不要提交到 Git。

## 开源许可

本项目已完全开源，采用 MIT License。你可以自由使用、复制、修改、分发和二次开发，但需要保留许可证和版权声明。

参与贡献前请阅读：

- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `docs/compliance-and-licenses.md`

请不要向仓库提交真实 API key、token、未授权视频/音频素材或模型权重。

## 合规与贡献

如何提交 issue：请提供系统、Python、FFmpeg 状态、复现命令或 UI 操作路径、期望结果和实际结果；不要上传未授权剧集片段、真实人声音频、API key 或 token。

如何贡献 profile：优先提交不含密钥的 `examples/` 示例，使用 `{{ api_key }}`、`YOUR_API_KEY` 或 `KEY=VALUE` 变量占位；说明模型/服务许可证、输入输出 JSON 合约、最小验证命令和是否需要本地模型目录。

不接受模型权重、真实影视片段或 API key。相关合规细节见 `docs/compliance-and-licenses.md`。

## 快速开始

请在项目目录执行命令：

```powershell
cd F:\GZYproject\Intelligent-Voice-Over
uv run ivo doctor
uv run pytest
```

生成不含真实影视素材的合成样片，用于验证导入、预览和导出流程：

```powershell
uv run python .\scripts\create_sample_media.py --output-dir .\sample_media
```

如果你在其他目录执行，可以显式指定项目：

```powershell
uv run --project F:\GZYproject\Intelligent-Voice-Over ivo doctor
```

## 常用开发命令

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
uv run ivo doctor
uv run ivo doctor-models
uv run ivo model smoke-asr --output .\scratch\asr-smoke.json --dry-run
uv run ivo model smoke-adapters --output .\scratch\adapter-smoke.json
```

启动桌面 UI：

```powershell
uv run python -m ivo.app
```

运行 mock 端到端测试：

```powershell
uv run pytest tests/test_e2e_mock_pipeline.py -v
```

## CLI 预览

生成一个不依赖真实 AI 模型的 mock 预览项目：

```powershell
uv run ivo mock-preview .\sample.mp4 .\demo-output --project-name "Episode 01" --source-language en
```

使用本地命令 profile 跑预览链路：

```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.mock.json --project-name "Episode 01" --source-language en --no-watermark
```

真实模型 profile 建议增加 `--require-readiness --models-dir .\models`，在包、模型目录或 engine command 文件缺失时提前退出，不创建半成品项目。快速真实预览优先使用已经验收过的 F5 GPU 小预览 profile：

```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_separation_asr_tts_f5_gpu_small.json --project-name "Episode 01" --source-language ja --require-readiness --models-dir .\models --resume-existing --no-watermark
```

正式质量优先流程使用完整 GPU + 说话人分离 + LM Studio 翻译 profile。运行前需要确认 `.venv-pyannote` 可用、LM Studio 已启动，并且 `http://127.0.0.1:1995/v1/models` 能看到 profile 中的模型 ID：

```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_full_gpu_f5_diarization.json --translation-profile .\examples\http_translation_lm_studio_qwen36_35b.example.json --project-name "Full GPU Episode 01" --source-language ja --require-readiness --models-dir .\models --resume-existing --no-watermark
```

如果真实本地模型运行中途失败，保留同一个输出目录和项目名，修复模型环境或 profile 后可用 `--resume-existing` 复用已有 `.ivoproj`、job 状态和已完成的文件阶段产物：

```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_dry_run.json --project-name "Episode 01" --source-language en --resume-existing --no-watermark
```

运行真实模型前，可以先静态校验本地命令 profiles：

```powershell
uv run ivo validate-local-profiles .\examples\local_command_profiles.real_dry_run.json --json
uv run ivo check-local-readiness .\examples\local_command_profiles.real_full_gpu_f5_diarization.json --models-dir .\models --json
```

批量处理一个目录里的多集视频，并为每个视频生成独立 `.ivoproj`：

```powershell
uv run ivo batch-local-preview .\episodes .\demo-output --profiles .\examples\local_command_profiles.real_dry_run.json --source-language en --no-watermark
```

批处理可以加 `--report .\demo-output\batch-report.json` 写出机器可读结果；单个视频失败时会继续处理后续视频，最后用非零退出码汇总失败数。已经生成过 `renders/local-preview.mp4` 的项目可以用 `--skip-existing` 跳过；需要继续已有 `.ivoproj` 的阶段状态时使用 `--resume-existing`，适合长剧集续跑。

使用真实模型接入脚本的 dry-run profile 验证命令合约：

```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_dry_run.json --project-name "Episode 01" --source-language en --target-text "seg-001=嗯，你好。" --no-watermark
```

## 自定义线上 API

自定义线上模型 API 通过 `ApiAdapterProfile` 描述，并可保存为 JSON profile。当前 CLI 支持添加和查看 HTTP adapter profile：

```powershell
uv run ivo adapter add-http .\adapters.json --id translator --stage translation --url https://api.example.test/translate --response target_text=$.text --optional-response style_prompt --file-upload audio=audio_path
uv run ivo adapter list .\adapters.json
uv run ivo validate-http-profile .\examples\http_translation_profile.example.json --json
```

本地命令预览也可以把翻译阶段切到 HTTP API：

```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.mock.json --translation-profile .\examples\http_translation_profile.example.json --translation-var api_key=YOUR_API_KEY --project-name "Episode 01" --source-language en
```

人声分离阶段也可以切到 HTTP API。示例 profile 使用 `vocals_base64` 和 `background_base64` 返回两路音频：
```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.mock.json --separation-profile .\examples\http_separation_profile.example.json --separation-var api_key=YOUR_API_KEY --project-name "Episode 01" --source-language en
```

也可以把 ASR / 转写阶段切到 HTTP API。ASR profile 需要返回 `segments` 列表，字段格式与本地 ASR 命令输出一致：
```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.mock.json --asr-profile .\examples\http_asr_profile.example.json --asr-var api_key=YOUR_API_KEY --project-name "Episode 01" --source-language en
```

说话人分离阶段也可以切到 HTTP API。该 profile 返回说话人时间范围，流水线会映射到 ASR 片段：
```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.mock.json --diarization-profile .\examples\http_diarization_profile.example.json --diarization-var api_key=YOUR_API_KEY --project-name "Episode 01" --source-language en
```

也可以把 TTS / 音色克隆阶段切到 HTTP API。TTS API profile 可以返回 `audio_base64`，也可以返回本地可读的 `audio_path`：

```powershell
uv run ivo local-preview .\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.mock.json --tts-profile .\examples\http_tts_profile.example.json --tts-var api_key=YOUR_API_KEY --project-name "Episode 01" --source-language en
```

## 本地模型

项目不默认打包模型权重。你可以先登记本地模型路径和许可证确认：

```powershell
uv run ivo model add-local .\models.json --id cosyvoice-local --stage tts --name "CosyVoice Local" --path .\models\cosyvoice --language zh --confirm-license
uv run ivo model list .\models.json
```

真实本地模型可通过 `LocalCommandAdapter` 接入：把 ASR、人声分离、TTS/音色克隆模型包装成命令行脚本，输出标准 JSON 文件，流水线即可继续处理。示例脚本在 `examples/local_commands/`。

更多说明见：

- `docs/local-model-setup.md`
- `docs/local-model-command-profiles.md`
- `docs/evaluation/real-video-evaluation.md`
- `docs/ui-local-preview.md`
- `docs/windows-packaging.md`
