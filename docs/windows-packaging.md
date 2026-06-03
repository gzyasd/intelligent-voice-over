# Windows 打包与安装说明

本项目提供 `scripts/build_windows_package.py` 作为 Windows 桌面包构建入口。脚本会通过 `uv tool run pyinstaller` 调用 PyInstaller，把 PySide6 桌面入口、`src/` 源码、`examples/` 示例 profile 和 `docs/` 文档一起放入发布目录。

## 构建前准备

1. 在 Windows 终端进入项目目录。
2. 确认 Python 版本为 3.10。
3. 确认 FFmpeg 已安装并能在终端中运行：

```powershell
ffmpeg -version
```

如果没有 FFmpeg，可以用：

```powershell
winget install Gyan.FFmpeg
```

安装后重新打开终端，再运行 `uv run ivo doctor` 检查。

## 预览构建命令

先用 dry-run 查看将要执行的 PyInstaller 命令：

```powershell
uv run python .\scripts\build_windows_package.py --dry-run --output-dir .\dist
```

输出中应包含 `uv tool run pyinstaller`、`--collect-all PySide6`、`--add-data examples;examples` 和 `--add-data docs;docs`。

## 生成桌面程序

确认 dry-run 命令无误后运行：

```powershell
uv run python .\scripts\build_windows_package.py --output-dir .\dist
```

构建完成后，入口程序位于：

```text
dist\IntelligentVoiceOver\IntelligentVoiceOver.exe
```

## 安装与分发

- 将 `dist\IntelligentVoiceOver\` 整个目录复制到目标机器。
- 目标机器仍需要可用的 FFmpeg，因为导入、预览和最终导出都依赖 FFmpeg。
- 本地模型权重不会被打包进程序。需要在目标机器上按 `docs/local-model-command-profiles.md` 配置模型目录、许可证确认和本地命令 profile。
- 自定义线上 API profile 可以直接随 `examples/` 或项目配置文件分发，但 API key 建议通过 UI 的 `KEY=VALUE` 输入框或 CLI 的 `--*-var` 参数填写，不要写死在公开 profile 文件中。

## 验收检查

在目标机器上启动 `IntelligentVoiceOver.exe` 后，建议按顺序检查：

1. 新建或打开 `.ivoproj` 项目。
2. 在“模型设置”页选择本地命令 profiles JSON。
3. 用 mock profile 跑一次“本地命令预览”。
4. 审核时间线后执行“最终导出”。

如果程序启动失败，优先检查 FFmpeg、显卡驱动、本地模型依赖和被安全软件隔离的文件。
