# 客户端易用性调整说明

## 本轮目标

本轮调整面向中文用户的首次使用体验：

- 新建项目弹窗必须有明确的“创建项目 / 取消”按钮。
- 下拉选项展示中文，但程序内部仍使用稳定的英文代码值。
- 模型配置页默认走“本地模型目录 + 一键检查”的主路径。
- 在线 API、逐阶段 profile、变量映射等高级项默认收进“高级配置”。

## 模型目录放在哪里

默认模型目录是程序目录下的 `models`，例如：

```text
IntelligentVoiceOver/
  models/
    asr/
    separation/
    diarization/
    tts/
    llm/
```

如果模型已经下载在其他磁盘，也可以在客户端“模型设置”页点击“选择模型目录”，指定已有目录。程序不会强制把模型复制到项目目录。

## 普通用户推荐流程

1. 把模型放在默认 `models` 目录，或在“模型设置”页选择已有模型目录。
2. 保持默认本地命令配置。
3. 点击“刷新模型目录检查”。
4. 点击“检查本地模型是否就绪”。
5. 回到主界面创建项目并运行“本地命令预览”。

## 本地命令配置是什么

“本地命令配置”是一个 JSON 文件，用来告诉程序每个处理阶段应该调用哪个本地命令或脚本。例如：

- 人声分离：把视频音频拆成 vocals/background。
- 语音识别：把原语言语音转成字幕文本。
- 说话人识别：判断每句话是谁说的。
- 翻译：把原文改写成目标语言台词。
- 语音合成：按目标台词和参考声音生成配音片段。

普通用户不需要手写这个 JSON。客户端会默认指向项目里的示例配置；如果你只是在默认 `models` 目录放好推荐模型，优先使用 `examples/local_command_profiles.real_gpu_fast_preview.json` 或更高质量的 GPU 示例即可。只有在你更换模型目录、脚本路径、命令参数，或接入自己写的本地模型服务时，才需要编辑或另选这个 JSON。

配置文件里的核心字段通常是：

```json
{
  "asr": {
    "id": "faster-whisper-gpu",
    "stage": "asr",
    "command": [
      "{{ python_executable }}",
      "examples/local_commands/faster_whisper_asr.py",
      "--audio",
      "{{ audio_path }}",
      "--device",
      "cuda"
    ],
    "output_json_path": "{{ project_path }}/asr.json"
  }
}
```

其中 `{{ audio_path }}`、`{{ project_path }}` 这类内容是程序运行时自动替换的变量，用户通常不用改。

## 高级配置

“高级配置（本地命令 / 在线 API）”用于调试本地命令 profile、在线 API profile、变量、响应映射和文件上传字段。普通用户不需要一开始配置这些内容。

高级配置中每个输入框都会显示示例：

- `API 配置 JSON`：填写 profile 文件路径，例如 `examples/http_translation_lm_studio_qwen36_35b.example.json`。
- `变量 KEY=VALUE`：填写运行时变量，例如 `api_key=lm-studio,temperature=0.2`。
- `URL`：填写接口地址，例如 `http://127.0.0.1:1995/v1/chat/completions`。
- `响应映射`：告诉程序从 API 响应中取哪个字段，例如 `target_text=$.choices[0].message.content`。
- `文件上传字段`：告诉程序上传音频时字段名对应哪个路径变量，例如 `audio=audio_path`。
