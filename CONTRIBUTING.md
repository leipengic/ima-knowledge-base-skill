# 贡献指南（Contributing）

感谢你对 ima-knowledge-base-skill 的关注！欢迎通过以下方式参与贡献。

## 行为准则

参与本项目即表示你同意遵守我们的[行为准则](CODE_OF_CONDUCT.md)。

## 如何贡献

### 报告 Bug

1. 先在 [Issues](https://github.com/leipengic/ima-knowledge-base-skill/issues) 中搜索是否已有人报告相同问题。
2. 提交新 issue 时请包含：
   - 环境信息（操作系统、Python 版本）；
   - 复现步骤与报错信息（请脱敏，勿贴 API Key / Client ID）；
   - 涉及的接口或脚本（如 `ima_api.py`、`upload_file.py`）。

### 提出功能建议

在 issue 中说明功能要解决的问题、使用场景与期望行为。

### 提交代码（Pull Request）

1. Fork 本仓库并克隆到本地；
2. 从 `main` 分支创建功能分支：`git checkout -b feature/xxx`；
3. 保持代码风格一致，测试通过后再提交；
4. 推送并创建 Pull Request，说明改动内容与原因。

## 开发约定

- **零依赖**：仅使用 Python 3.8+ 标准库，不要引入第三方包；
- **安全优先**：新增网络访问仅允许 `ima.qq.com` 与腾讯云 COS 官方域名，并保持内置 SSRF 防护；凭证只能从环境变量或配置文件读取，绝不写入磁盘或日志；
- 新增接口请在 `references/api.md` 中同步补充字段、枚举与错误码说明；
- 请勿在代码、提交或 issue 中夹带任何凭证（Client ID / API Key / COS 签名）。

## 目录速览

| 文件/目录 | 职责 |
|---|---|
| `SKILL.md` | 技能说明（使用前提、脚本用法、接口决策表、安全约束） |
| `references/api.md` | IMA OpenAPI 完整接口参考 |
| `scripts/ima_api.py` | 通用 API 调用客户端 |
| `scripts/upload_file.py` | 本地文件上传（含 COS 上传签名） |

感谢你的贡献！
