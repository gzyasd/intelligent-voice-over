# 智能视频配音 (Intelligent Voice Over)

> 本地优先的 Windows 桌面端 AI 视频配音工具 —— 将英文 / 日文 / 韩文视频对白重新配成自然的中文音频。

![Electron](https://img.shields.io/badge/Electron-31-blue)
![Vue](https://img.shields.io/badge/Vue-3-42b883)
![Python](https://img.shields.io/badge/python-3.10-blue)
![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-orange)
![Platform](https://img.shields.io/badge/platform-Windows-blue)

[English](./README_EN.md) | **中文**

---

## 为什么选择 IVO

- **本地优先**：核心流水线在本地运行，模型权重不上传云端，你的视频素材不离开电脑。
- **双模式接入**：既支持本地模型（Demucs / faster-whisper / pyannote / F5-TTS / CosyVoice），也支持云端 API（OpenAI / Deepgram / ElevenLabs / 阿里云 / 讯飞 等）。
- **现代化桌面端**：Electron + Vue 3 + FastAPI 三层架构，响应式 UI，从项目创建到时间线审片全流程可视化操作，无需命令行。
- **断点续跑**：每个阶段独立记录状态，中途失败后修复环境即可从断点继续，不浪费已完成的产物。
- **合规内置**：导出时自动嵌入 AI 配音元数据，支持可见水印，确保 AI 生成内容透明标注。
- **批量处理**：支持整季剧集批量跑，单集失败不影响后续，最终汇总报告。

## 架构

```
┌─────────────────────────────────────────────┐
│              Electron 壳 (主进程)             │
│   管理窗口生命周期、启动/停止 Python 服务      │
├─────────────────────────────────────────────┤
│           Vue 3 渲染进程 (前端)               │
│   项目管理 / 时间线编辑 / 模型配置 / 运行日志  │
├─────────────────────────────────────────────┤
│         FastAPI Python 服务 (后端)            │
│   流水线编排 / 适配器调度 / SQLite 存储        │
├─────────────────────────────────────────────┤
│              本地模型 / HTTP API              │
│   Demucs / faster-whisper / pyannote / F5-TTS │
└─────────────────────────────────────────────┘
```

- **前端**：Vue 3 + Vite + Naive UI，TypeScript 严格模式
- **后端**：FastAPI + uvicorn，PyInstaller 打包为独立可执行文件
- **桌面壳**：Electron 31，负责窗口管理和 Python 服务生命周期
- **通信**：前端通过 HTTP/WebSocket 调用本地 Python 服务（127.0.0.1:17000-17999）

## 流水线

```
源视频
  │
  ├─ 1. 导入          复制源视频到项目
  ├─ 2. 音频提取      FFmpeg 提取标准化 WAV
  ├─ 3. 人声分离      Demucs / HTTP API → vocals.wav + background.wav
  ├─ 4. 语音转写      faster-whisper / HTTP API → 带时间戳的片段
  ├─ 5. 说话人分离    pyannote / HTTP API（可选）→ 分配说话人 ID
  ├─ 6. 文本翻译      LM Studio / HTTP API → 中文文本
  ├─ 7. 语音合成      F5-TTS / CosyVoice / HTTP API → 逐片段中文音频
  └─ 8. 混合导出      FFmpeg 混合背景音 + 对齐片段 + 水印 → 最终 MP4
```

每个阶段独立记录状态，支持断点续跑。

## 快速开始

### 方式一：下载安装包（推荐普通用户）

1. 前往 [Releases 页面](https://github.com/gzyasd/intelligent-voice-over/releases) 下载最新版 `IVO.Setup.x.x.x.exe`
2. 双击运行，按提示安装
3. **安装 AI 运行环境**（必需，见下方「安装 AI 运行环境」）
4. 从开始菜单或桌面快捷方式启动 IVO
5. 首次使用前需配置本地模型（见下方「本地模型配置」）

> 安装包已内置 FFmpeg 和 Python 后端运行时，无需额外安装。

#### 安装 AI 运行环境

IVO 的本地模型流水线依赖两个 Python 环境：`.venv`（主环境，含 torch / demucs / faster-whisper / F5-TTS 等）和 `.venv-pyannote`（说话人分离）。由于体积较大（合计约 6 GB），它们不打包进安装程序，需要单独安装。提供两种方式，任选其一：

**方式 A：下载预置环境包（推荐，离线可用）**

由于 GitHub 单文件 2 GB 限制，环境包已分卷上传到 Release：

1. 主环境 `.venv`（约 3.5 GB）：
   - 下载 `ivo-venv-portable.zip.01.part`、`ivo-venv-portable.zip.02.part`、`merge-ivo-venv-portable.bat`
   - 将三个文件放在同一文件夹，双击 `merge-ivo-venv-portable.bat` 合并出 `ivo-venv-portable.zip`
   - 解压该 zip，将得到的 `.venv` 文件夹复制到 IVO 安装目录的 `resources\` 下
2. 说话人分离环境 `.venv-pyannote`（约 2.7 GB）：
   - 下载 `ivo-venv-pyannote-portable.zip.01.part`、`ivo-venv-pyannote-portable.zip.02.part`、`merge-ivo-venv-pyannote-portable.bat`
   - 同上合并出 `ivo-venv-pyannote-portable.zip`，解压后将 `.venv-pyannote` 文件夹复制到 `resources\` 下

安装完成后，IVO 安装目录结构应为：

```
IVO/
├── IVO.exe
└── resources/
    ├── python/            （后端服务，安装时自带）
    ├── ffmpeg/bin/        （音视频处理，安装时自带）
    ├── .venv/             （主 AI 环境，手动下载解压）
    └── .venv-pyannote/   （说话人分离环境，手动下载解压）
```

**方式 B：应用内自动安装（在线，可选镜像源）**

启动 IVO 后，若检测到环境缺失，「设置」页面会显示警告。点击「自动安装环境」，选择镜像源（官方 / 清华 / 阿里 / 中科大），向导会自动创建两个 venv 并安装依赖，全程可视化进度。

### 方式二：从源码构建（推荐开发者）

#### 前置要求

- Windows 10/11
- [Node.js](https://nodejs.org/) 20+
- [pnpm](https://pnpm.io/) 10+
- [Python](https://www.python.org/) 3.10
- [uv](https://docs.astral.sh/uv/) 包管理器

#### 安装依赖

```powershell
git clone <repo-url>
cd Intelligent-Voice-Over

# 安装前端依赖
pnpm install

# 安装 Python 依赖
uv sync --dev
```

#### 开发模式运行

```powershell
# 同时启动前端开发服务器和 Electron
pnpm dev
```

#### 打包构建

> **PowerShell 执行策略提示**：如果运行 `pnpm` 时报错 `无法加载文件 pnpm.ps1，因为在此系统上禁止运行脚本`，有两种解决方式：
>
> 1. **使用 `.cmd` 后缀**（推荐，无需管理员权限）：直接调用 `pnpm.cmd` 代替 `pnpm`，例如 `pnpm.cmd run build:win`
> 2. **修改执行策略**（需管理员权限的 PowerShell）：`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

完整打包流程分三步：构建前端 → 打包 Python 后端 → 打包 Electron 安装包。

```powershell
# 1. 构建前端（Vue 3 + Vite，输出到 dist/renderer/ 和 dist-electron/）
pnpm.cmd run build:frontend

# 2. 打包 Python 后端（PyInstaller，输出到 dist/python/ivo-server.exe）
pnpm.cmd run build:python

# 3. 打包 Electron 安装包（NSIS，输出到 dist-installer3/）
#    build:win 会自动依次执行 build:frontend + build:python + electron-builder
pnpm.cmd run build:win
```

也可以单独执行某一步：

```powershell
# 仅构建前端
pnpm.cmd run build:frontend

# 仅打包 Python 后端
pnpm.cmd run build:python

# 仅打包 Electron 安装包（前端和 Python 产物已就绪时）
pnpm.cmd exec electron-builder --win
```

构建产物位于 `dist-installer3/` 目录：

- `IVO Setup 0.1.0.exe` — NSIS 安装包（约 230MB）
- `win-unpacked/IVO.exe` — 免安装版

> **注意**：安装包不包含 `.venv` 和 `.venv-pyannote`（超过 NSIS 32 位内存映射限制）。终端用户请按上方「方式一 → 安装 AI 运行环境」从 Release 下载预置环境包，或在应用内自动安装。开发者本机已有 `.venv` 和 `.venv-pyannote` 时，可运行 `scripts/copy-venv-to-install.ps1` 直接复制到安装目录：

```powershell
# 开发者本机已有 venv 时，复制到安装目录
.\scripts\copy-venv-to-install.ps1 -InstallDir "C:\Program Files\IVO"
```

> **打包失败排查**：如果 `electron-builder` 报错 `The process cannot access the file because it is being used by another process`（通常是 `app.asar` 被占用），可能是上次的 IVO 进程未退出或 Windows Defender 正在扫描。解决方法：
> 1. 确认没有 IVO/ivo-server/electron 进程运行：`Get-Process -Name "IVO","ivo-server","electron" -ErrorAction SilentlyContinue`
> 2. 修改 `electron-builder.yml` 的 `directories.output` 为新目录名（如 `dist-installer4`）绕过文件锁
> 3. 或重启系统后重试

### 本地模型配置

项目不打包模型权重。首次使用本地模型流水线前，需要下载以下模型：

| 阶段 | 推荐模型 | 下载方式 |
|------|----------|----------|
| 人声分离 | Demucs `htdemucs_ft` | 首次运行自动下载 |
| 语音转写 | faster-whisper `large-v3` | HuggingFace Hub |
| 说话人分离 | pyannote community-1 | 需接受 HF 模型条款 |
| 文本翻译 | LM Studio + Qwen3 | 本地 HTTP 服务 |
| 语音合成 | F5-TTS | HuggingFace Hub |

模型目录结构：

```
models/
  asr/
    faster-whisper-large-v3/
  diarization/
    pyannote-community-1/
  tts/
    f5-tts/
```

在桌面端「模型中心」页面选择模型目录，点击「检查就绪」即可验证模型是否完整。

### FFmpeg 说明

安装包已内置 FFmpeg。从源码运行时，仓库的 `ffmpeg/bin/` 目录也包含 FFmpeg，无需单独安装。

## 桌面端使用

桌面端采用左侧导航布局：

| 页面 | 用途 |
|------|------|
| **首页** | 快速入口和最近项目 |
| **项目库** | 管理所有 `.ivoproj` 项目，支持打开、查看文件夹、删除 |
| **当前项目** | 生成进度、时间线审片、单句重生成、最终导出 |
| **模型中心** | 选择模型目录、一键检查就绪状态、管理模型方案 |
| **模型服务** | 配置云端 API 提供商（OpenAI / Deepgram / ElevenLabs 等） |
| **设置** | 项目目录、最近项目等用户偏好 |

推荐工作流：

1. 在「模型中心」选择模型目录并一键检查就绪状态
2. 通过 4 步向导新建项目（选择视频 → 选择语言 → 选择模型方案 → 确认）
3. 在「当前项目 → 生成进度」查看阶段和句子级进度
4. 完成后在「时间线」审片，可单句重生成
5. 确认后执行最终导出（含合规水印）

## 两种接入模式

### 本地模型

通过模型方案（scheme）配置本地模型，所有推理在本地 GPU/CPU 上运行：

| 阶段 | 推荐模型 | 说明 |
|------|----------|------|
| 人声分离 | Demucs `htdemucs_ft` | GPU 优先 |
| 语音转写 | faster-whisper `large-v3` | GPU/float16 |
| 说话人分离 | pyannote community-1 | 需接受 HF 模型条款 |
| 文本翻译 | LM Studio + Qwen3 | 本地 HTTP 服务 |
| 语音合成 | F5-TTS / CosyVoice | F5 权重为 CC-BY-NC，商用需换权重 |

### 云端 API

通过 `ApiAdapterProfile` 描述 HTTP API，所有阶段均可替换为云端服务。内置支持的云端提供商：

| 提供商 | 支持阶段 |
|--------|----------|
| OpenAI | ASR + 说话人分离 + TTS |
| Deepgram | ASR |
| AudioShake | 人声分离 |
| LALAL.AI | 人声分离 |
| 阿里云百炼 | ASR |
| 阿里云 Qwen-TTS | TTS |
| ElevenLabs | TTS |
| Anthropic | 翻译 |
| OpenAI 兼容 | 翻译 |
| 讯飞开放平台 | ASR + 说话人分离 |

## 项目结构

```
{project}.ivoproj/
  project.json       项目元数据
  segments.sqlite    时间线片段存储
  jobs.sqlite        阶段执行状态
  speakers.json      说话人配置
  settings.json      项目设置
  assets/            源视频、提取的音频
  work/              人声、背景音、生成的片段音频
  renders/           最终输出视频
```

## 开发

> 如果 `pnpm` 命令因 PowerShell 执行策略报错，请改用 `pnpm.cmd`（见上方「打包构建」一节的说明）。

```powershell
# 前端类型检查
pnpm.cmd run typecheck

# 前端单元测试
pnpm.cmd test

# Python 代码检查
uv run ruff check .

# Python 类型检查（严格模式）
uv run mypy src

# Python 全部测试
uv run pytest
```

## 技术栈

| 层 | 技术 |
|----|------|
| 桌面壳 | Electron 31 |
| 前端 | Vue 3 + Vite + Naive UI + TypeScript |
| 后端 | FastAPI + uvicorn + Pydantic v2 |
| 存储 | SQLite（原生 sqlite3，无 ORM） |
| 模板 | Jinja2（SandboxedEnvironment + StrictUndefined） |
| HTTP | httpx |
| 打包 | PyInstaller（Python）+ electron-builder（Electron） |

## 许可证

本项目源码采用 **PolyForm Noncommercial License 1.0.0**。你可以在非商业用途下查看、学习、修改、运行和分发本项目代码，但**未经作者书面授权，不得用于商业用途**。

> PolyForm Noncommercial License 不是 OSI 认证的开源许可证，因为它限制商业使用。本项目采用「源码开放 / 非商业使用许可」的发布方式。

商业使用包括但不限于：付费产品、SaaS 服务、企业内部生产部署、付费交付、商业项目集成、收费部署/咨询/运维。商业授权说明见 [COMMERCIAL-LICENSE.md](./COMMERCIAL-LICENSE.md)。

**第三方模型注意事项**：F5-TTS 代码是 MIT，但默认预训练权重为 CC-BY-NC，商业用途前必须换用许可证合适的模型或服务。第三方模型许可证彼此独立，不会因为本项目代码采用 PolyForm Noncommercial 而自动变成同一许可证。

## 贡献

参与贡献前请阅读：

- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)
- [SECURITY.md](./SECURITY.md)
- [docs/compliance-and-licenses.md](./docs/compliance-and-licenses.md)

请不要向仓库提交真实 API key、token、未授权视频/音频素材或模型权重。

## 更多文档

- [本地模型环境配置](./docs/local-model-setup.md)
- [本地命令 Profile 指南](./docs/local-model-command-profiles.md)
- [HTTP API Profile 指南](./docs/http-api-profiles.md)
- [合规与许可证](./docs/compliance-and-licenses.md)
