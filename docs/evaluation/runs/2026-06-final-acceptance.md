# 2026-06 最终验收记录

## 本地质量门

执行日期：2026-06-05。

命令与结果：

- `uv run pytest`：264 passed。
- `uv run ruff check .`：通过。
- `uv run mypy src`：通过，47 个源码文件无类型错误。
- `uv run ivo doctor`：Python 3.10.6 可用；FFmpeg 可用；NVIDIA 工具可用。
- `uv run ivo doctor-models`：能区分 installed/missing，并输出安装、下载、许可证和验证提示。

## Mock 端到端

命令：

```powershell
uv run python .\scripts\create_sample_media.py --output-dir .\sample_media
uv run ivo mock-preview .\sample_media\en_synthetic_1min.mp4 .\scratch\final-acceptance-mock --project-name "Mock Final" --source-language en
uv run ivo evaluate-project ".\scratch\final-acceptance-mock\Mock Final.ivoproj" --format json
```

结果：

- 导出视频：`scratch\final-acceptance-mock\Mock Final.ivoproj\renders\preview.mp4`。
- 评估：1 个片段，状态 `rendered`；质量标记包含 `duration_ok`、`missing_reference_audio`、`silent_audio`，符合 mock 音频预期。

## 真实 20 秒 F5 本地链路

样片来源：用户本机授权测试视频，截取到系统临时目录，不提交仓库。

命令：

```powershell
uv run ivo local-preview "$env:TEMP\ivo_final_real_probe\jp_probe_20s.mp4" "$env:TEMP\ivo_final_f5_20s" --profiles .\examples\local_command_profiles.real_separation_asr_tts_f5_cpu_small.json --project-name JP-Final-F5-20s --source-language ja --require-readiness --resume-existing --no-watermark
uv run ivo evaluate-project "$env:TEMP\ivo_final_f5_20s\JP-Final-F5-20s.ivoproj" --format json
```

结果：

- 导出视频：`%TEMP%\ivo_final_f5_20s\JP-Final-F5-20s.ivoproj\renders\local-preview.mp4`。
- 片段：4 个，全部 `rendered`。
- 质量标记：`duration_ok: 4`。
- 作业阶段：`import`、`audio_extract`、`separation`、`asr`、`translation`、`tts`、`export` 全部 `completed`。

## 真实 1 分钟 F5 本地链路

命令：

```powershell
uv run ivo local-preview "$env:TEMP\ivo_final_real_probe\jp_probe_60s.mp4" "$env:TEMP\ivo_final_f5_60s" --profiles .\examples\local_command_profiles.real_separation_asr_tts_f5_cpu_small.json --project-name JP-Final-F5-60s --source-language ja --require-readiness --resume-existing --no-watermark
uv run ivo evaluate-project "$env:TEMP\ivo_final_f5_60s\JP-Final-F5-60s.ivoproj" --format json
```

结果：

- 导出视频：`%TEMP%\ivo_final_f5_60s\JP-Final-F5-60s.ivoproj\renders\local-preview.mp4`。
- 片段：6 个，全部 `rendered`。
- 质量标记：`duration_ok: 6`。
- 作业阶段：`import`、`audio_extract`、`separation`、`asr`、`translation`、`tts`、`export` 全部 `completed`。
- 中断后项目可通过 `--resume-existing` 继续；本次验收期间已验证生成片段和最终导出保留在临时项目目录。

## 打包 dry-run

命令：

```powershell
uv run python scripts/build_windows_package.py --dry-run --output-dir dist
```

结果：

- PyInstaller 命令生成成功。
- release manifest 排除 `models`、`测试视频`、`sample_media`、`scratch`、`*.mp4`、`*.wav`、`.env`。
- 不打包模型权重、未授权素材或密钥。

## 已知限制

- 当前虚拟环境中的 `torch` 是 `2.5.1+cpu`，虽然本机有 RTX 5090 和 NVIDIA 工具，但这次真实 F5 验收仍按 CPU 路线完成。
- GPU profile 已提供，后续若要显著提速，需要切换 CUDA 版 PyTorch，并按 `examples/local_command_profiles.real_gpu_quality.json` 或 `examples/local_command_profiles.real_gpu_fast_preview.json` 重新做真实 GPU 验收。
- CosyVoice profile 和安装脚本已补齐，但本次最终验收的真实 TTS 路线仍以 F5-TTS 为准。
- 真实素材、生成视频、音频片段和模型权重均保存在本机临时目录或忽略目录，不进入 Git。

## 结论

截至 2026-06-05，本项目已达到可开源预览和继续真实样片迭代的状态：本地/HTTP profile 架构、桌面 UI、运行日志、时间线审核、质量统计、恢复重跑、模型安装脚本、GPU profile、Windows 打包 dry-run、合规文档、mock E2E、真实 20 秒与真实 1 分钟 F5 本地链路均已完成或验证。
