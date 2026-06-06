# 2026-06-05 F5-TTS 最小真实生成验收

## 目标

验证项目的 `f5_tts_command.py` wrapper 可以通过 engine command 调用 F5-TTS 官方 CLI，生成真实中文 WAV，而不是只停留在 dry-run。

## 环境

- Python：3.10.6。
- F5-TTS：`f5-tts==1.1.20`。
- PyTorch：`torch==2.5.1`。
- Transformers：`transformers<5`，实测 `transformers 5.x` 与当前 Torch 组合不兼容。
- 设备：CPU。

## 输入

- 参考音频：从用户本机授权测试视频分离出的人声音轨截取 5 秒，保存在本机临时目录。
- 参考文本：来自真实 ASR 的日语片段文本。
- 生成文本：一句短中文测试文本。
- 仓库策略：不提交参考音频、生成音频或任何真实素材。

## 命令形态

```powershell
uv run python .\examples\local_commands\f5_tts_command.py --text "你好，我们继续测试。" --speaker speaker-1 --audio-out C:\Users\Administrator\AppData\Local\Temp\ivo_real_probe\f5_real.wav --json-out C:\Users\Administrator\AppData\Local\Temp\ivo_real_probe\f5_real.json --reference-audio C:\Users\Administrator\AppData\Local\Temp\ivo_real_probe\f5_ref_5s.wav --reference-text "参考音频文本" --duration-ms 2500 --engine-command-json-file .\examples\engine_commands\f5_tts_engine_command.example.json
```

## 结果

- F5-TTS 官方 CLI 可启动。
- 首次运行成功下载 Vocos 和 F5TTS_v1_Base 权重到本机 Hugging Face cache。
- 成功生成 `f5_real.wav` 和 `f5_real.json`。
- CPU 单句生成约 66 秒。

## 后续

- 将 `examples/local_command_profiles.real_tts_f5.json` 接入 engine command file。
- 在完整 `local-preview` 中把 TTS 从 dry-run 切到 F5-TTS，先跑短片段，再扩大到 1-3 分钟。
- 商业用途前必须重新确认 F5-TTS 预训练权重许可；当前默认权重为 CC-BY-NC。
