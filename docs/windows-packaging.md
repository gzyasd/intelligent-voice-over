# Windows 打包与安装说明

本项目提供 `scripts/build_windows_package.py` 作为 Windows 桌面包构建入口。脚本会通过 `uv run pyinstaller` 调用 PyInstaller，把 PySide6 桌面入口、`src/` 源码、`examples/` 示例 profile、`docs/` 文档和 FFmpeg 一起放入发布目录。

## 构建前准备

1. 在 Windows 终端进入项目目录。
2. 确认 Python 版本为 3.10。
3. 确认打包机器上已安装 FFmpeg，并能在终端中运行。打包脚本会把当前 FFmpeg 目录内置到发布包中：

```powershell
ffmpeg -version
```

如果没有 FFmpeg，可以用：

```powershell
winget install Gyan.FFmpeg
```

安装后重新打开终端，再运行 `uv run ivo doctor` 检查。

如果 FFmpeg 不在 PATH 中，可以显式指定目录。目录可以是 FFmpeg 根目录，也可以是包含 `ffmpeg.exe` 的目录：

```powershell
uv run python .\scripts\build_windows_package.py --ffmpeg-dir "C:\path\to\ffmpeg-8.1.1-full_build" --output-dir .\dist
```

如果只想验证打包程序、导入、预览和导出流程，可以先生成合成样片，避免使用任何未授权剧集片段：

```powershell
uv run python .\scripts\create_sample_media.py --output-dir .\sample_media
```

这些文件是 FFmpeg 生成的测试画面和纯音，不代表真实 ASR、翻译或 TTS 质量。

## 预览构建命令

先用 dry-run 查看将要执行的 PyInstaller 命令：

```powershell
uv run python .\scripts\build_windows_package.py --dry-run --output-dir .\dist
```

输出中应包含 `uv run pyinstaller`、`--collect-all PySide6`、`--add-data <项目路径>\examples;examples`、`--add-data <项目路径>\docs;docs` 和 `--add-data <FFmpeg路径>;ffmpeg`。
dry-run 还会输出将要写入的 `release-manifest.json` 预览，里面记录版本、入口程序、打包包含项和明确排除的模型权重、素材目录与密钥。

## 生成桌面程序

确认 dry-run 命令无误后运行：

```powershell
uv run python .\scripts\build_windows_package.py --output-dir .\dist
```

也可以运行包含测试、ruff、mypy 和打包步骤的 PowerShell 包装脚本：

```powershell
.\scripts\package-windows.ps1
```

脚本路径：`scripts/package-windows.ps1`。

构建完成后，入口程序位于：

```text
dist\IntelligentVoiceOver\IntelligentVoiceOver.exe
```

同时会生成一个完整便携包：

```text
dist\IntelligentVoiceOver-0.1.0-win64-portable.zip
```

同一目录还会生成发布清单：

```text
dist\IntelligentVoiceOver\release-manifest.json
```

发布前请检查清单中的 `included_data`、`excluded_paths` 和 `excluded_secrets`，确认没有把模型权重、未授权素材或真实 token 放进发布包。

## 安装与分发

- 推荐分发 `dist\IntelligentVoiceOver-0.1.0-win64-portable.zip`，用户解压后双击 `IntelligentVoiceOver\IntelligentVoiceOver.exe`。
- 不要只复制 `IntelligentVoiceOver.exe`。该 exe 依赖同目录下的 `_internal` 文件夹；如果只复制 exe，会出现 `Failed to load Python DLL ... _internal\python310.dll` 这类错误。
- 如果不使用 zip，也必须将 `dist\IntelligentVoiceOver\` 整个目录复制到目标机器。
- FFmpeg 已随发布包内置。程序运行时会优先使用包内 `ffmpeg\bin\ffmpeg.exe` 和 `ffmpeg\bin\ffprobe.exe`，然后才回退到本机环境变量或 PATH。
- 本地模型权重不会被打包进程序。需要在目标机器上按 `docs/local-model-command-profiles.md` 配置模型目录、许可证确认和本地命令 profile。
- 本地模型运行时、GPU 驱动、CUDA、LM Studio 或其他模型服务仍需用户在目标机器上自行安装和配置。
- 自定义线上 API profile 可以直接随 `examples/` 或项目配置文件分发，但 API key 建议通过 UI 的 `KEY=VALUE` 输入框或 CLI 的 `--*-var` 参数填写，不要写死在公开 profile 文件中。
- 发布包、示例目录和 GitHub Release 不能包含未授权影视素材、真实人声音频、分离后音轨、TTS 生成音频、模型权重或真实密钥。

## GitHub Release 草稿说明

创建 GitHub Release 草稿时，建议在说明中明确：

- 本 release 只包含应用代码、示例 profile 和文档。
- FFmpeg 已内置在 Windows 发布包中，用户通常不需要额外安装 FFmpeg。
- 模型权重不会被打包，用户需要自行下载并确认第三方模型许可证。
- GPU 驱动、CUDA、LM Studio 和本地模型运行环境需要用户在目标机器上自行准备。
- 请只处理自己拥有授权的视频和音频素材，不要上传或分发未授权剧集片段。
- API key、Hugging Face token 和 ModelScope token 应通过本机环境变量、UI 变量输入或私有配置提供。

## 验收检查

在目标机器上启动 `IntelligentVoiceOver.exe` 后，建议按顺序检查：

1. 新建或打开 `.ivoproj` 项目。
2. 在“模型设置”页选择本地命令 profiles JSON。
3. 用 mock profile 跑一次“本地命令预览”。
4. 审核时间线后执行“最终导出”。

如果程序启动失败，优先检查包内 `ffmpeg` 目录是否完整、显卡驱动、本地模型依赖和被安全软件隔离的文件。
