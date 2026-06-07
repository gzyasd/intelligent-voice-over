# 贡献指南

感谢你愿意参与 Intelligent Voice Over。这个项目的目标是做一个本地优先、可插拔、可审查的 AI 视频配音工具，尤其关注英文、日文、韩文到中文配音的自然度与可控性。

## 开发环境

```powershell
cd F:\GZYproject\Intelligent-Voice-Over
uv sync
uv run ivo doctor
uv run pytest
```

常用质量检查：

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

## 提交前检查

- 你的贡献将按本项目当前许可证 PolyForm Noncommercial License 1.0.0 授权给项目维护者和其他用户。
- 请确认你有权提交相关代码、文档、配置或示例；不要提交无法按本项目许可证分发的内容。
- 新功能或行为变更请先补测试。
- 本地模型权重、真实 API key、视频素材和生成产物不要提交到仓库。
- HTTP profile 示例请使用 `{{ api_key }}`、`YOUR_API_KEY` 等占位符，不要写入真实凭据。
- 涉及音视频处理、AI 配音或导出流程的改动，请保留合规提醒和 AI 元数据/水印相关能力。

## Issue 和 PR

提交 issue 时建议包含：

- 你使用的系统、Python 版本和 FFmpeg 状态。
- 复现命令或 UI 操作路径。
- 期望结果和实际结果。
- 可公开分享的最小样例，避免上传未授权视频或音频素材。

提交 PR 时建议包含：

- 改动摘要。
- 已运行的验证命令。
- 对用户工作流的影响。
- 任何剩余限制或后续计划。

## Profile 贡献

欢迎贡献本地命令 profile、HTTP profile 或 engine command 示例。请确保：

- 不包含真实 API key、token、cookie、私钥或 `.env`。
- 不包含模型权重、真实影视片段、真实人声音频或生成产物。
- 明确说明模型或服务许可证、下载渠道、最小验证命令和 JSON 输入输出合约。
- 对需要 Hugging Face、ModelScope 或商业服务账号的 profile，只写占位符和配置说明。
