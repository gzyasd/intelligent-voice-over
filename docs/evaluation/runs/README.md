# 评测运行记录

这里用于保存不含真实素材的评测报告。每个报告只记录模型组合、命令、评分、问题和结论，不提交原始视频、音频、分离结果、TTS 输出或最终导出视频。

## 命名规则

```text
YYYY-MM-DD-language-model-stack.md
```

示例：

```text
2026-06-03-en-fasterwhisper-cosyvoice3.md
2026-06-03-ja-qwen3-f5tts.md
```

## 允许提交

- 模型组合名称和版本。
- 本地环境摘要。
- 不含密钥的命令。
- 主观评分。
- 自动质量标记统计。
- 下一轮改进项。

## 不允许提交

- 未授权影视素材。
- 原片截图、切片、音频、人声分离结果、TTS 结果或导出视频。
- API key、Hugging Face token、ModelScope token。
- 可识别未授权剧集、集数、角色或时间戳的信息。

评测模板见 `docs/evaluation/real-video-evaluation.md`。
