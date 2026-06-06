# 真实视频样片评测规范

本规范用于记录真实本地模型或线上 API 组合在授权视频片段上的效果。仓库不保存美剧、日剧、韩剧原片、切片、音频或模型权重；这里只保存评测方法、空白模板和不含敏感素材的结论。

当前验收矩阵见 `docs/evaluation/acceptance-matrix.md`。截至 2026-06-06，项目已经用授权日语样片跑通 Demucs + faster-whisper + pyannote + LM Studio + F5-TTS 的完整 GPU 预览链路；其中 3 分 21 秒真实视频已完整导出，56 个片段全部 `rendered`。后续评测应继续按 20 秒、1-3 分钟、5-10 分钟、整集四个层级推进，重点转向长视频稳定性、多语言覆盖和人工质量评分。

## 素材要求

- 只能使用你拥有授权的本地视频文件、公开可测试素材或自制素材。
- 不向 GitHub 上传原片、截取片段、分离后人声、背景音、TTS 结果或最终导出视频。
- 每个样片建议从 1-3 分钟开始；P1 再扩大到 3-5 分钟多说话人片段。
- 文件名和报告中不要包含可识别的未授权剧集标题、集数或角色名。

## 推荐样片矩阵

| 编号 | 源语言 | 时长 | 人物数 | 目标 |
| --- | --- | --- | --- | --- |
| EN-01 | 英文 | 1-3 分钟 | 1-2 人 | 验证英文 ASR、自然中文翻译、基础音色一致性 |
| JA-01 | 日文 | 1-3 分钟 | 1-2 人 | 验证日文 ASR、停顿/语气词、中文口语化 |
| KO-01 | 韩文 | 1-3 分钟 | 1-2 人 | 验证韩文 ASR、情绪和语速控制 |
| MIX-01 | 任意 | 3-5 分钟 | 3 人以上 | 验证说话人分离、审核、局部重生成和最终导出 |

## 运行记录模板

````markdown
# Evaluation Run: YYYY-MM-DD-短名称

## 基本信息

- 本地日期：
- 操作系统：
- GPU / 显存：
- FFmpeg 版本：
- 项目 commit：
- 源语言：
- 样片时长：
- 人物数：
- 素材授权说明：

## 模型组合

- 人声分离：
- ASR：
- 说话人分离：
- 翻译：
- TTS / 音色克隆：
- 导出参数：

## 命令

```powershell
uv run ivo doctor
uv run ivo doctor-models --models-dir .\models
uv run ivo local-preview .\sample_media\sample.mp4 .\demo-output --profiles .\examples\local_command_profiles.real_diarization.json --translation-profile .\examples\http_translation_openai_compatible.example.json --translation-var api_key=LOCAL_TOKEN --translation-var base_url=http://127.0.0.1:8000 --translation-var model=Qwen3-8B --project-name "Eval" --source-language en --no-watermark
uv run ivo evaluate-project ".\demo-output\Eval.ivoproj" --format markdown --output ".\docs\evaluation\runs\YYYY-MM-DD-eval.md"
```

## 评分

| 项目 | 分数 1-5 | 备注 |
| --- | --- | --- |
| ASR 准确度 |  |  |
| 说话人分离 |  |  |
| 中文翻译自然度 |  |  |
| 语气词/停顿保留 |  |  |
| 情绪一致性 |  |  |
| 音色相似度 |  |  |
| 语速/时长匹配 |  |  |
| 背景音保留 |  |  |
| 最终可看性 |  |  |

## 自动质量标记

- `duration_mismatch`：
- `speaker_unmatched`：
- `missing_reference_audio`：
- 其他：

## 结论

- 本轮是否通过 P0：
- 最影响观看体验的问题：
- 下一轮优先修改：
````

## P0 通过标准

- 1 分钟授权样片能完整导出视频。
- 输出视频包含中文配音、背景音、AI 配音元数据。
- 主要对白可理解，没有大面积空白音频。
- CLI 或 UI 失败时能指出具体阶段和 provider。
- `uv run ivo evaluate-project <project.ivoproj> --format markdown` 能输出状态、质量标记和作业状态摘要。
- 相关变更通过 `uv run pytest`、`uv run ruff check .`、`uv run mypy src`。

## P1 通过标准

- 3-5 分钟多说话人样片可完成审核、单句重生成和最终导出。
- 用户能在 UI 中选择本地 profile 或线上 API profile。

## 批量验收命令

```powershell
uv run ivo evaluate-batch .\demo-output --output .\demo-output\batch-evaluation.json
```

`evaluate-batch` 会扫描目录下的 `.ivoproj` 项目，输出每集片段数量、质量标记、失败 job 和整体汇总，适合批处理后统一验收。
- 评测报告能清楚说明模型组合优劣，而不是只给主观印象。
- 仓库中没有模型权重、真实密钥或未授权素材。
