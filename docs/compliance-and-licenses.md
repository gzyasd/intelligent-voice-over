# 合规与许可证说明

## 项目代码

项目代码许可证：PolyForm Noncommercial License 1.0.0。你可以在非商业用途下查看、学习、修改、运行和分发本仓库代码，但商业使用必须先获得项目作者的书面授权。商业授权说明见仓库根目录 `COMMERCIAL-LICENSE.md`。

请注意：PolyForm Noncommercial License 不是 OSI 认证的开源许可证，因为它限制商业使用。本项目采用“源码开放 / 非商业使用许可”的发布方式。

## 第三方模型

第三方模型许可证彼此独立，不会因为本项目代码采用 PolyForm Noncommercial License 而自动获得同样权限。下载、运行、分发或商用前，请重新确认对应模型卡、仓库说明和服务条款。

- F5-TTS：代码通常按其上游许可证处理，但常用预训练权重包含 CC-BY-NC 限制，商业用途前必须换用许可证合适的权重或服务。
- CosyVoice：使用前重新确认模型卡、下载渠道和具体权重许可证；不同版本、镜像和派生模型的许可证可能不同。
- pyannote：通常需要登录 Hugging Face 并接受模型条款；不要把 Hugging Face token、HF_TOKEN 或下载缓存提交到仓库。

## 用户素材

用户必须确认拥有视频处理权利。请只处理自己拥有版权、授权或合法使用权的视频、音频、字幕和角色声音素材。

仓库、Issue、PR、Release 和示例 profile 不接受：

- 模型权重或模型缓存。
- 真实影视片段、真实人声音频、分离后音轨或 TTS 生成音频。
- API key、token、cookie、私钥、账号凭据或 `.env`。

## 导出标识

导出结果应写入 AI 配音元数据，并保留可选可见水印能力。关闭可见水印不代表可以隐藏 AI 生成事实；是否需要显著标识应按具体平台、地区法规和素材授权要求判断。

## 发布检查

发布 GitHub Release 或 Windows 包前，请确认：

- `models/`、`测试视频/`、`sample_media/`、`scratch/` 没有进入发布包。
- `*.mp4`、`*.wav`、模型权重、API key 和 token 没有进入 Git。
- README、SECURITY、CONTRIBUTING 和本文件仍然说明第三方模型许可证和用户素材授权责任。
