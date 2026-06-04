# 桌面 UI 本地命令预览说明

主窗口提供“本地命令预览”入口，可以从“模型设置”页读取本地命令 profiles JSON，以及可选的人声分离、ASR、说话人分离、翻译、TTS HTTP profile，然后调用与 CLI 相同的 `run_local_command_preview` 流水线。

## 使用步骤

1. 点击主窗口“新建项目”，在项目向导中选择源视频、输出目录和源语言；也可以点击“打开项目”，选择已有 `.ivoproj` 目录。
2. 打开“模型设置”页。
3. 在“本地命令 profiles JSON”填写或浏览选择本地命令 profile 文件，例如：

```text
F:\GZYproject\Intelligent-Voice-Over\examples\local_command_profiles.real_dry_run.json
```

在同一页可以填写“本地模型安装脚本输出”，例如 `scripts/setup-local-models.ps1`，然后点击“生成本地模型安装脚本”。UI 会根据“本地模型路径”生成与 `uv run ivo model write-setup-script` 相同的 PowerShell 脚本，方便后续安装 Python 包、创建模型目录和下载 Hugging Face 模型。

选择本地命令 profiles 后，可以先点击“校验本地命令 profile”，静态检查关键阶段和输出 JSON 占位，避免完整预览运行到一半才发现 profile 写错。

4. 如果人声分离阶段使用线上 API，在“人声分离 HTTP profile JSON”填写或浏览选择：

```text
F:\GZYproject\Intelligent-Voice-Over\examples\http_separation_profile.example.json
```

5. 如果 ASR / 转写阶段使用线上 API，在“ASR HTTP profile JSON”填写或浏览选择：

```text
F:\GZYproject\Intelligent-Voice-Over\examples\http_asr_profile.example.json
```

6. 如果说话人分离阶段使用线上 API，在“说话人分离 HTTP profile JSON”填写或浏览选择：

```text
F:\GZYproject\Intelligent-Voice-Over\examples\http_diarization_profile.example.json
```

7. 如果翻译阶段使用线上 API，在“翻译 HTTP profile JSON”填写或浏览选择：

```text
F:\GZYproject\Intelligent-Voice-Over\examples\http_translation_profile.example.json
```

8. 如果 TTS / 音色克隆阶段使用线上 API，在“TTS HTTP profile JSON”填写或浏览选择：

```text
F:\GZYproject\Intelligent-Voice-Over\examples\http_tts_profile.example.json
```

9. 如果 HTTP profile 使用了 `{{ api_key }}` 等变量，在对应阶段的“变量 KEY=VALUE”输入框填写，例如：

```text
api_key=YOUR_API_KEY
```

多个变量可以用逗号或换行分隔。

10. 点击“本地命令预览”。

命令行模式和桌面 UI 都支持把人声分离、ASR、说话人分离、翻译、TTS 任一阶段切到线上 HTTP API；未配置 HTTP profile 的阶段会继续使用本地命令 profiles。

## 时间线编辑

时间线表格支持逐句审校和重生成：

- 可编辑：说话人、中文译文、情绪、状态。
- 只读：片段 ID、原文、质量标记。
- 状态必须是 `pending`、`running`、`needs_review`、`approved`、`failed`、`rendered` 之一。
- “保存”会调用 `TimelineEditor.save_row(row)` 并写回项目数据库。
- “重生成”会先在 UI 线程保存当前行的可见编辑内容，再读取本地命令 profiles JSON 中的 `tts` profile，或优先使用 TTS HTTP profile，对该片段重新合成；完成后刷新时间线，失败时恢复按钮并弹出错误提示。

## 最终导出

预览生成并审校时间线后，可以点击主窗口“最终导出”：

1. 选择导出路径。
2. 勾选素材处理和导出权利确认。
3. 按需启用可见水印并填写水印文字。
4. 主窗口会根据当前项目的源视频、`work/background.wav`、`work/generated_segments/*.wav` 和时间线片段生成导出请求，并通过后台 worker 执行最终 FFmpeg 导出。

最终导出会写入 AI 配音元数据；未勾选权利确认时，核心导出函数会拒绝导出。如果导出路径或权利确认缺失，主窗口会弹出提示；如果 FFmpeg 或导出命令失败，也会显示失败状态并弹出错误提示。

## 错误提示

本地命令预览或单句重生成失败时，主窗口会显示失败状态并弹出错误提示。常见错误包括：

- profiles 路径不存在；
- 本地命令脚本运行失败；
- HTTP 人声分离、ASR、说话人分离、翻译或 TTS API 超时，或返回非成功状态；
- FFmpeg 不可用或导出失败。

本地命令失败时，错误文本会尽量包含阶段、provider、渲染后的命令、退出码、stderr 摘要和期望的输出 JSON 路径。这样可以直接定位是模型路径、Python 包、token、输出文件还是脚本参数问题。

## 当前限制

- 当前 UI 已接入核心流水线，并对本地命令预览、单句重生成和最终导出提供 `PipelineWorker` 后台执行入口；真实模型或 FFmpeg 导出运行时间较长时，可以避免直接阻塞主线程。
- `real_dry_run` profile 只验证命令合约，不代表真实模型质量。去掉 `--dry-run` 前，需要先按 `docs/local-model-command-profiles.md` 安装依赖并调整模型参数。
