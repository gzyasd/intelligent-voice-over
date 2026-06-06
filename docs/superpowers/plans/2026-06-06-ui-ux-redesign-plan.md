# 智能视频配音 UI/UX 重设计实施计划

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前偏工程工具的桌面客户端重设计为普通中文用户也能顺畅使用的本地优先智能配音软件，隐藏 JSON 和命令细节，提供清晰项目管理、模型配置、生成进度和审片导出流程。

**Architecture:** 保留现有 PySide6、pipeline、adapter、project 数据结构，新增一层面向用户的 UI 状态模型和配置预设模型。核心思路是“预设驱动 + 向导式流程 + 进度事件 + 项目库”，让用户通过卡片、开关、下拉项、状态徽标和文件选择完成配置，而不是直接面对 JSON profile。

**Tech Stack:** Python 3.10、PySide6、Pydantic、SQLite、现有 `DubbingProject`/`JobStore`/`LocalCommandPipelineProfiles`/HTTP adapter/local command adapter、pytest-qt。

---

## 1. 现状问题

当前核心功能已经可用，但客户端的产品形态仍接近开发者工具：

- 主界面是竖排按钮加 Tab，缺少“首页/项目库/当前项目/设置”的清晰结构。
- “模型设置”暴露本地命令配置、HTTP profile、JSON、KEY=VALUE、响应映射等实现细节，普通用户无法判断该填什么。
- 新建项目后虽然有“开始生成配音（完整流程）”，但用户仍不知道生成前是否配置完成、生成中正在做什么、失败后该如何恢复。
- 生成过程只通过文字日志和最终状态反馈，用户无法看到阶段进度、当前处理内容、耗时、剩余步骤、可重试位置。
- 缺少项目管理入口，用户不方便查看以往项目、打开项目文件夹、查看生成视频、继续未完成任务。
- 当前视觉风格是默认 Qt 控件堆叠，缺少现代桌面软件的层次、留白、主次按钮、状态色和一致的间距。

## 2. 设计原则

- **普通用户优先**：默认界面不出现 JSON、profile、adapter、命令、占位符、响应映射等词。高级功能可以存在，但必须放在“开发者/高级”折叠区。
- **预设优先**：模型配置以“本机高质量”“本机快速预览”“LM Studio 翻译 + 本地模型”“自定义在线 API”等预设卡片呈现。
- **可解释进度**：生成过程按阶段展示，每个阶段有中文名称、说明、状态、耗时、错误处理和可恢复提示。
- **项目即中心**：启动后先看到项目库和明显的新建入口，用户能快速回到旧项目、打开输出文件夹、继续生成或查看结果。
- **克制美观**：参考苹果式设计的“简洁、留白、柔和阴影、浅色背景、圆角卡片、清晰主按钮”，不直接复制任何 Apple 品牌元素。
- **本地优先且可扩展**：默认支持包内运行环境和本地模型目录，同时允许用户在图形界面新增在线 API 或混合配置。
- **每一步可测试**：每个界面重构都先写 pytest-qt 测试，再实现。

## 3. 目标信息架构

新主窗口采用左侧导航 + 右侧内容区：

- **首页**
  - 最近项目列表。
  - “新建配音项目”主按钮。
  - “检查模型配置”状态卡。
  - “打开已有项目”次按钮。
- **项目库**
  - 扫描默认 `runs/` 和用户手动打开过的 `.ivoproj`。
  - 项目卡片显示名称、源语言、创建/修改时间、生成状态、输出视频状态。
  - 操作：打开项目、继续生成、打开文件夹、打开成品视频、从列表移除。
- **当前项目**
  - 顶部项目摘要：视频名、语言、剧集类型、质量预设、当前状态。
  - 主流程条：导入视频、分离人声、识别字幕、识别角色、翻译、生成配音、合成视频、审片导出。
  - 主按钮根据状态变化：开始生成、继续生成、重试失败阶段、查看成品、导出最终视频。
- **模型中心**
  - 普通模式：预设卡片、模型目录选择、LM Studio 连接检查、在线 API 管理。
  - 高级模式：导入/导出 JSON profile、逐阶段命令、响应映射和变量。
- **审片**
  - 时间线审核、角色管理、单句试听、重生成、问题过滤。
- **设置**
  - 默认模型目录、默认项目目录、输出目录策略、GPU 优先、语言偏好、日志级别。

## 4. 视觉方向

采用一个轻量设计系统，不引入复杂第三方 UI 库：

- 背景：浅灰 `#F5F5F7`，内容面板白色 `#FFFFFF`。
- 文字：Windows 下优先 `Microsoft YaHei UI`，字号 13-14；标题 20-28；辅助文字 12。
- 主色：蓝色 `#007AFF`，成功绿 `#34C759`，警告橙 `#FF9500`，失败红 `#FF3B30`。
- 圆角：卡片 10-12px，按钮 8-10px。
- 间距：窗口边距 24px，卡片内边距 16px，列表间距 12px。
- 按钮层级：主按钮蓝底白字，次按钮白底灰边，危险按钮红色文字。
- 不使用大面积渐变、深色背景、装饰性图案；重点是安静、整洁、稳定。

## 5. 用户流程

### 5.1 首次启动

1. 用户打开客户端。
2. 首页显示“欢迎使用智能视频配音”，并展示三张状态卡：
   - 模型目录：未选择/已就绪。
   - LM Studio：未连接/已连接。
   - 最近项目：空/最近项目数。
3. 如果模型未就绪，显示“设置模型”主按钮。
4. 如果模型就绪，显示“新建配音项目”主按钮。

### 5.2 模型配置

普通用户只看到这些控件：

- 模型目录：选择文件夹，默认 `程序目录/models`。
- 翻译模型：下拉选择
  - LM Studio 本机模型（推荐，适合 Qwen3.6 35B）。
  - 本地命令 LLM。
  - 在线 API。
- 配音质量：分段控件
  - 快速预览。
  - 高质量。
- 处理硬件：开关
  - 优先使用 GPU。
- 一键检查：显示 ASR、分离、说话人识别、TTS、翻译服务是否就绪。

用户不需要选择 JSON 文件。界面内部根据预设映射到现有 `examples/*.json`。

### 5.3 新建项目

新建向导分 4 步：

1. 选择视频
   - 支持拖放视频或浏览。
   - 自动从文件名生成项目名。
2. 选择内容类型
   - 美剧、日剧、韩剧、其他。
   - 源语言：英语、日语、韩语。
   - 目标语言默认中文。
3. 选择生成方案
   - 使用当前推荐模型配置。
   - 快速预览或高质量。
   - 显示预计耗时提示。
4. 确认
   - 项目保存位置。
   - 输出文件默认位置。
   - 创建后是否立即开始生成。

### 5.4 生成过程

生成页展示：

- 总进度条。
- 当前阶段卡片。
- 阶段列表：
  - 导入视频。
  - 提取音频。
  - 分离人声/背景。
  - 识别字幕。
  - 识别角色。
  - 翻译改写。
  - 生成配音。
  - 合成视频。
  - 完成。
- 每个阶段显示状态：等待中、进行中、已完成、已跳过、失败。
- TTS 阶段显示片段进度：`第 12 / 83 句`。
- 底部显示可展开日志，默认折叠。
- 失败时显示“发生了什么 / 如何修复 / 重试此阶段”。

### 5.5 项目库

项目库支持：

- 最近项目卡片。
- 搜索项目名。
- 按状态筛选：未开始、生成中、失败、已完成。
- 打开项目。
- 继续生成。
- 打开项目文件夹。
- 打开成品视频。
- 从列表移除。

项目库不删除实际项目文件，除非用户在二次确认弹窗中选择“同时删除本地文件”。

## 6. 数据与配置设计

### 6.1 用户全局设置

新增 `src/ivo/core/user_settings.py`，默认存储在 `.ivo-work/user-settings.json`：

- `models_dir: str`
- `projects_dir: str`
- `preferred_preset_id: str`
- `prefer_gpu: bool`
- `lm_studio_base_url: str`
- `recent_projects: list[str]`
- `theme: "light"`

### 6.2 模型预设

新增 `src/ivo/core/model_presets.py`：

- `ModelPreset`
  - `id`
  - `display_name`
  - `description`
  - `quality`
  - `local_profiles_path`
  - `translation_profile_path`
  - `requires_lm_studio`
  - `requires_gpu`
  - `recommended_models`
- 内置预设：
  - `local_quality_lmstudio_qwen_f5`
  - `local_fast_gpu`
  - `local_cpu_preview`
  - `online_custom`

### 6.3 项目索引

新增 `src/ivo/core/project_library.py`：

- 扫描 `runs/**/*.ivoproj`。
- 合并 `recent_projects`。
- 读取 `project.json`、`settings.json`、`jobs.sqlite` 和 `renders/`。
- 生成 `ProjectLibraryItem`：
  - 项目名。
  - 路径。
  - 源视频。
  - 语言。
  - 更新时间。
  - 生成状态。
  - 最终视频路径。

### 6.4 进度事件

新增 `src/ivo/pipeline/progress.py`：

- `PipelineStage`
- `PipelineProgressEvent`
  - `stage`
  - `stage_label`
  - `status`
  - `message`
  - `overall_percent`
  - `current_item`
  - `total_items`
  - `output_path`

`run_local_command_preview` 增加可选参数：

- `progress_callback: Callable[[PipelineProgressEvent], None] | None = None`

每个 `_run_stage` 开始/完成/失败时发送事件。TTS 循环中每处理一个 segment 发送片段级进度事件。

## 7. 文件结构计划

### 新增文件

- `src/ivo/core/user_settings.py`：全局用户设置读写。
- `src/ivo/core/model_presets.py`：面向用户的模型预设定义和 profile 映射。
- `src/ivo/core/project_library.py`：项目库扫描、索引、状态摘要。
- `src/ivo/pipeline/progress.py`：进度事件模型。
- `src/ivo/ui/theme.py`：浅色主题、QSS、颜色和间距常量。
- `src/ivo/ui/app_shell.py`：左侧导航和页面容器。
- `src/ivo/ui/home_page.py`：首页。
- `src/ivo/ui/project_library_page.py`：项目库页面。
- `src/ivo/ui/project_overview_page.py`：当前项目总览与主流程。
- `src/ivo/ui/model_center.py`：普通用户模型中心。
- `src/ivo/ui/generation_progress.py`：生成进度组件。
- `src/ivo/ui/advanced_model_settings.py`：现有高级 JSON/profile 配置迁移位置。

### 修改文件

- `src/ivo/ui/main_window.py`：从按钮堆叠改为 app shell。
- `src/ivo/ui/model_settings.py`：拆分为普通模型中心和高级设置。
- `src/ivo/ui/project_wizard.py`：改为多步向导。
- `src/ivo/ui/timeline_editor.py`：审片页视觉和操作优化。
- `src/ivo/ui/workers.py`：支持进度事件 signal。
- `src/ivo/pipeline/local_command_preview.py`：发送进度事件。
- `src/ivo/core/settings.py`：项目设置引用用户预设 ID，而不是暴露 profile 路径。
- `docs/ui-usability-adjustment.md`：更新为普通用户操作说明。

### 测试文件

- `tests/core/test_user_settings.py`
- `tests/core/test_model_presets.py`
- `tests/core/test_project_library.py`
- `tests/pipeline/test_progress_events.py`
- `tests/ui/test_app_shell.py`
- `tests/ui/test_home_page.py`
- `tests/ui/test_project_library_page.py`
- `tests/ui/test_model_center.py`
- `tests/ui/test_generation_progress.py`
- 更新现有 `tests/ui/test_main_window*.py`、`tests/ui/test_project_wizard*.py`。

## 8. 实施任务

### Task 1: 建立视觉主题和 App Shell

**Files:**
- Create: `src/ivo/ui/theme.py`
- Create: `src/ivo/ui/app_shell.py`
- Modify: `src/ivo/ui/main_window.py`
- Test: `tests/ui/test_app_shell.py`
- Test: `tests/ui/test_main_window.py`

- [ ] **Step 1: 写失败测试，要求主窗口使用左侧导航**

测试断言：

- 主窗口存在导航项：首页、项目库、当前项目、模型中心、设置。
- 主按钮不再竖排堆在窗口顶部。
- 默认页面是首页。

- [ ] **Step 2: 实现 `theme.py`**

提供：

- `apply_app_theme(app: QApplication) -> None`
- `CARD_STYLE`
- `PRIMARY_BUTTON_STYLE`
- `SECONDARY_BUTTON_STYLE`
- 色彩常量。

- [ ] **Step 3: 实现 `AppShell`**

包含左侧导航和 `QStackedWidget` 内容区。导航点击切换页面。

- [ ] **Step 4: 改造 `MainWindow`**

`MainWindow` 只负责组装 shell、连接项目状态和页面事件。

- [ ] **Step 5: 跑测试**

```powershell
uv run pytest tests\ui\test_app_shell.py tests\ui\test_main_window.py -q
```

### Task 2: 项目库

**Files:**
- Create: `src/ivo/core/project_library.py`
- Create: `src/ivo/ui/project_library_page.py`
- Modify: `src/ivo/core/user_settings.py`
- Test: `tests/core/test_project_library.py`
- Test: `tests/ui/test_project_library_page.py`

- [ ] **Step 1: 写失败测试，扫描 `runs/*.ivoproj`**

测试创建两个项目，一个完成、一个失败，断言项目库能读出名称、路径、状态和成品路径。

- [ ] **Step 2: 实现 `ProjectLibraryItem`**

字段：

- `name`
- `path`
- `source_video_path`
- `source_language`
- `target_language`
- `updated_at`
- `status`
- `final_video_path`

- [ ] **Step 3: 实现项目库扫描**

函数：

- `scan_project_library(projects_dir: Path, recent_projects: list[Path]) -> list[ProjectLibraryItem]`

扫描失败的项目不能让整个列表失败；返回 item 时附加状态 `unreadable` 和错误摘要。

- [ ] **Step 4: 实现项目库 UI**

卡片操作：

- 打开项目。
- 继续生成。
- 打开文件夹。
- 打开成品视频。
- 从列表移除。

- [ ] **Step 5: 跑测试**

```powershell
uv run pytest tests\core\test_project_library.py tests\ui\test_project_library_page.py -q
```

### Task 3: 用户全局设置

**Files:**
- Create: `src/ivo/core/user_settings.py`
- Modify: `src/ivo/workspace_paths.py`
- Test: `tests/core/test_user_settings.py`

- [ ] **Step 1: 写失败测试，默认设置指向程序目录**

断言：

- 默认模型目录是 `<runtime_root>/models`。
- 默认项目目录是 `<runtime_root>/runs`。
- 默认 `prefer_gpu` 为 `True`。
- 默认 LM Studio 地址是 `http://127.0.0.1:1995/v1`。

- [ ] **Step 2: 实现设置模型**

Pydantic 模型：

- `UserSettings`
- `UserSettingsStore`

- [ ] **Step 3: 支持最近项目**

`add_recent_project(path)` 去重，并把最新项目放到最前。

- [ ] **Step 4: 跑测试**

```powershell
uv run pytest tests\core\test_user_settings.py -q
```

### Task 4: 模型预设与模型中心

**Files:**
- Create: `src/ivo/core/model_presets.py`
- Create: `src/ivo/ui/model_center.py`
- Create: `src/ivo/ui/advanced_model_settings.py`
- Modify: `src/ivo/ui/model_settings.py`
- Test: `tests/core/test_model_presets.py`
- Test: `tests/ui/test_model_center.py`

- [ ] **Step 1: 写失败测试，普通模式不出现 JSON**

断言模型中心主界面不包含：

- `JSON`
- `profile`
- `adapter`
- `KEY=VALUE`
- `响应映射`

这些内容只允许出现在高级设置页。

- [ ] **Step 2: 定义内置模型预设**

至少包含：

- 本机高质量：本地分离 + faster-whisper large-v3 + pyannote + F5-TTS + LM Studio Qwen。
- 本机快速预览：GPU small/fast profile。
- CPU 快速预览：无 NVIDIA 时可用。
- 自定义在线 API：用户逐阶段指定服务。

- [ ] **Step 3: 模型中心 UI**

显示：

- 预设卡片。
- 模型目录选择。
- LM Studio 连接检查。
- 一键检查模型。
- 当前推荐操作。

- [ ] **Step 4: 新增在线 API 配置向导**

普通用户表单：

- 服务名称。
- 阶段：翻译、语音识别、语音合成、人声分离、说话人识别。
- API 地址。
- API Key。
- 模型名。
- 测试连接按钮。

高级映射字段折叠在“高级参数”里。

- [ ] **Step 5: 兼容现有 JSON profile**

内部仍保存为现有 profile 格式，避免重写 adapter 层。普通用户只看到“配置名称”和“是否可用”。

- [ ] **Step 6: 跑测试**

```powershell
uv run pytest tests\core\test_model_presets.py tests\ui\test_model_center.py -q
```

### Task 5: 新建项目向导重设计

**Files:**
- Modify: `src/ivo/ui/project_wizard.py`
- Test: `tests/ui/test_project_wizard_file_selection.py`
- Test: `tests/ui/test_main_window_project_wizard_flow.py`

- [ ] **Step 1: 写失败测试，向导是 4 步**

断言步骤标题：

- 选择视频。
- 内容与语言。
- 生成方案。
- 确认创建。

- [ ] **Step 2: 视频选择页**

支持：

- 浏览选择。
- 拖放文件。
- 自动生成项目名。
- 显示视频路径和文件大小。

- [ ] **Step 3: 内容与语言页**

控件：

- 源语言。
- 剧集类型。
- 翻译风格备注。
- 可选术语表，按钮文案改为“选择术语表”，不出现 JSON。

- [ ] **Step 4: 生成方案页**

控件：

- 质量：快速预览 / 高质量。
- 模型预设：使用当前推荐配置 / 重新选择。
- 显示模型就绪状态。

- [ ] **Step 5: 确认创建页**

显示摘要，并提供：

- 创建项目。
- 创建并开始生成。

- [ ] **Step 6: 跑测试**

```powershell
uv run pytest tests\ui\test_project_wizard_file_selection.py tests\ui\test_main_window_project_wizard_flow.py -q
```

### Task 6: 进度事件与生成页

**Files:**
- Create: `src/ivo/pipeline/progress.py`
- Create: `src/ivo/ui/generation_progress.py`
- Modify: `src/ivo/pipeline/local_command_preview.py`
- Modify: `src/ivo/ui/workers.py`
- Modify: `src/ivo/ui/main_window.py`
- Test: `tests/pipeline/test_progress_events.py`
- Test: `tests/ui/test_generation_progress.py`
- Test: `tests/ui/test_main_window_local_preview.py`

- [ ] **Step 1: 写失败测试，pipeline 发送阶段事件**

断言事件顺序包含：

- import started/completed
- audio_extract started/completed
- separation started/completed
- asr started/completed
- translation started/completed
- tts started/progress/completed
- export started/completed

- [ ] **Step 2: 实现 `PipelineProgressEvent`**

字段：

- `stage`
- `stage_label`
- `status`
- `message`
- `overall_percent`
- `current_item`
- `total_items`
- `output_path`

- [ ] **Step 3: 改造 `_run_stage`**

阶段开始、完成、失败都发送事件。已有 `JobStore` 仍负责可恢复状态。

- [ ] **Step 4: TTS 片段进度**

`_synthesize_segments` 每处理一个 segment 发送一次事件，显示 `第 N / 总数 句`。

- [ ] **Step 5: Worker signal**

`PipelineWorker` 增加 `progress = Signal(object)`，后台线程收到 callback 后发 signal 给 UI。

- [ ] **Step 6: 生成页 UI**

显示：

- 总进度。
- 当前阶段。
- 阶段列表。
- 当前处理句子。
- 可展开日志。
- 失败修复建议。

- [ ] **Step 7: 跑测试**

```powershell
uv run pytest tests\pipeline\test_progress_events.py tests\ui\test_generation_progress.py tests\ui\test_main_window_local_preview.py -q
```

### Task 7: 当前项目总览

**Files:**
- Create: `src/ivo/ui/project_overview_page.py`
- Modify: `src/ivo/ui/main_window.py`
- Test: `tests/ui/test_project_overview_page.py`

- [ ] **Step 1: 写失败测试，项目打开后显示摘要**

断言显示：

- 项目名。
- 源视频名。
- 源语言。
- 模型预设。
- 当前生成状态。

- [ ] **Step 2: 实现主操作按钮状态机**

状态：

- 无项目：新建项目。
- 项目未生成：开始生成。
- 有失败阶段：重试失败阶段。
- 已生成：查看成品。
- 已生成且有审核修改：重新生成修改片段。

- [ ] **Step 3: 文件入口**

提供：

- 打开项目文件夹。
- 打开生成视频。
- 打开日志。

- [ ] **Step 4: 跑测试**

```powershell
uv run pytest tests\ui\test_project_overview_page.py -q
```

### Task 8: 审片页优化

**Files:**
- Modify: `src/ivo/ui/timeline_editor.py`
- Test: `tests/ui/test_timeline_editor_actions.py`
- Test: `tests/ui/test_timeline_editor_editing.py`

- [ ] **Step 1: 写失败测试，审片页默认隐藏技术列**

普通模式不显示 segment id、质量 flag 原始英文值、style_prompt 原始字段名。

- [ ] **Step 2: 增加右侧详情面板**

点击某句后显示：

- 原文。
- 中文台词。
- 说话人。
- 情绪。
- 参考音频状态。
- 试听按钮。
- 重生成按钮。

- [ ] **Step 3: 增加问题过滤**

筛选：

- 全部。
- 待审核。
- 生成失败。
- 配音偏长。
- 缺参考声音。

- [ ] **Step 4: 跑测试**

```powershell
uv run pytest tests\ui\test_timeline_editor_actions.py tests\ui\test_timeline_editor_editing.py -q
```

### Task 9: 错误处理和空状态

**Files:**
- Create: `src/ivo/ui/empty_states.py`
- Modify: `src/ivo/ui/model_center.py`
- Modify: `src/ivo/ui/project_library_page.py`
- Modify: `src/ivo/ui/generation_progress.py`
- Test: `tests/ui/test_empty_states.py`

- [ ] **Step 1: 写失败测试，模型缺失有用户可懂提示**

示例文案：

- “没有找到 F5-TTS 模型。请把模型放到 models/tts/F5-TTS，或在模型中心选择已有目录。”

- [ ] **Step 2: 统一错误组件**

显示：

- 发生了什么。
- 为什么会发生。
- 下一步按钮。
- 详细日志折叠区。

- [ ] **Step 3: 空项目库状态**

显示：

- “还没有项目”。
- “新建配音项目”主按钮。
- “打开已有项目”次按钮。

- [ ] **Step 4: 跑测试**

```powershell
uv run pytest tests\ui\test_empty_states.py -q
```

### Task 10: 文档、验收和打包

**Files:**
- Modify: `docs/ui-usability-adjustment.md`
- Modify: `docs/windows-packaging.md`
- Modify: `README.md`
- Test: `tests/test_windows_packaging.py`

- [ ] **Step 1: 更新用户说明**

把用户流程改为：

1. 打开客户端。
2. 在模型中心选择模型目录和推荐预设。
3. 一键检查。
4. 新建项目。
5. 点击开始生成。
6. 在进度页查看阶段。
7. 审片和导出。

- [ ] **Step 2: 更新打包说明**

保留 `--skip-archive` 说明。需要刷新目录时只运行：

```powershell
uv run python .\scripts\build_windows_package.py --output-dir .\dist --skip-archive
```

- [ ] **Step 3: 全量验证**

```powershell
uv run ruff check .
uv run mypy src
uv run pytest
```

- [ ] **Step 4: 客户端目录刷新**

只刷新目录，不主动压缩：

```powershell
uv run python .\scripts\build_windows_package.py --output-dir .\dist --skip-archive
```

## 9. 里程碑

### Milestone A: 视觉外壳和项目库

完成 Task 1、Task 2、Task 3。用户打开软件后能看到现代化首页和项目库。

验收：

- 首页不是按钮堆叠。
- 能看到最近项目。
- 能打开项目文件夹和成品视频。

### Milestone B: 模型配置去 JSON 化

完成 Task 4。普通用户能通过预设完成模型配置。

验收：

- 普通模型中心不出现 JSON/profile/adapter。
- 能选择 LM Studio + 本地模型高质量预设。
- 能一键检查模型就绪。

### Milestone C: 新建和生成流程

完成 Task 5、Task 6、Task 7。用户能从新建项目一路看到生成进度。

验收：

- 新建向导有 4 个步骤。
- 可选择创建并开始生成。
- 生成过程有阶段进度和当前片段进度。
- 失败能重试。

### Milestone D: 审片和发布体验

完成 Task 8、Task 9、Task 10。用户能完成审片、重生成和导出。

验收：

- 审片页隐藏技术字段。
- 错误提示可理解。
- 文档与客户端流程一致。

## 10. 验收标准

- 普通用户主流程中不需要看到或编辑 JSON。
- 新用户能在 5 分钟内完成模型目录检查和新建项目。
- 项目创建后能明确知道下一步该做什么。
- 生成过程中能看到当前阶段和总进度。
- TTS 阶段能看到当前句子进度。
- 失败后能看到中文原因、建议操作和重试入口。
- 项目库能找回以往项目、打开项目文件夹和成品视频。
- UI 视觉统一，窗口缩放时不重叠、不裁切主要按钮。
- 所有新增 UI 都有 pytest-qt 覆盖。
- `uv run ruff check .`、`uv run mypy src`、`uv run pytest` 通过。

## 11. 风险和控制

- **风险：重构主窗口影响现有流程。** 控制：先保留旧 pipeline 和 adapter，只换 UI shell；每个页面用测试覆盖入口。
- **风险：隐藏 JSON 后高级用户无法调试。** 控制：保留“高级/开发者设置”，但默认折叠。
- **风险：进度百分比不精确。** 控制：先使用阶段权重和片段计数，标注为“预计进度”，避免承诺精确 ETA。
- **风险：项目库扫描慢。** 控制：优先扫描 `runs/` 第一层和 recent projects；后续再做后台扫描。
- **风险：样式在 Windows 不一致。** 控制：使用 Qt stylesheet 和固定系统字体，Playwright 不适用时用 pytest-qt 和截图人工验收。

## 12. 本计划不包含的事项

- 不重写模型推理核心。
- 不改模型权重下载策略。
- 不主动压缩便携包；需要刷新客户端目录时使用 `--skip-archive`。
- 不引入 Web 前端或 Electron。
- 不做深色模式，第一版只做浅色主题。

## 13. 自检结果

- 覆盖了用户提出的模型设置、创建项目、生成进度、项目管理、美观易用和隐藏 JSON 要求。
- 每个功能区域都有对应文件和测试。
- 没有要求用户直接编辑 JSON；JSON 仅作为高级兼容能力保留。
- 实施路径按里程碑拆分，可逐步提交和验证。
