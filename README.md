# ima-knowledge-base-skill

连接腾讯 IMA 知识库（https://ima.qq.com）的 Agent 技能包，提供一套基于 Python 标准库的知识库**读取**与**写入**能力，包括知识库搜索/浏览、本地文件上传、网页/微信文章导入、笔记添加、媒体原文读取等。

## 特性

- 零依赖：仅使用 Python 3.8+ 标准库，无需第三方包，跨 Windows / macOS / Linux
- 安全优先：仅访问 `ima.qq.com` 与腾讯云 COS 官方域名，内置 SSRF 防护；凭证只从环境变量或配置文件读取，绝不写入磁盘、绝不输出到日志
- 完整封装：覆盖知识库搜索、目录浏览、站内搜索、媒体原文、重名检查、文件上传、URL 导入、笔记添加等接口

## 依赖说明（零第三方库）

本项目**不依赖任何第三方包**，全部能力由 Python 3.8+ 标准库实现，因此没有 `requirements.txt`。

| 标准库 | 在项目中做的事 | 为什么这样选 |
|---|---|---|
| `urllib.request` / `urllib.parse` / `urllib.error` | `ima_api.py` 发起 HTTPS 请求、拼装查询串、处理 HTTP 错误码 | 只调用少量 REST 接口，无需为 `requests` 增加依赖；同时便于在请求层做域名白名单校验 |
| `hmac` / `hashlib` | 生成 OpenAPI 请求签名（`Client ID` + `API Key` 参与计算） | 接口签名机制要求 HMAC 摘要，标准库即可满足，避免引入加密相关三方包 |
| `mimetypes` | 上传文件时推断 `Content-Type` | 上传接口要求显式文件类型，标准库推断足够 |
| `json` | 请求体序列化与响应解析 | — |
| `argparse` | 命令行参数（`scripts/*.py` 的调用入口） | — |

> 安全约束：`ima_api.py` 会校验目标域名，仅允许 `ima.qq.com` 与腾讯云 COS（`*.myqcloud.com`），避免技能被引导访问任意地址（SSRF 防护）。

## 目录结构

```
ima-knowledge-base-skill/
├── SKILL.md                 # 技能说明（使用前提、脚本用法、接口决策表、安全约束）
├── README.md                # 本文件
├── references/
│   └── api.md               # IMA OpenAPI 完整接口参考（字段、枚举、错误码）
└── scripts/
    ├── ima_api.py           # 通用 API 调用客户端
    └── upload_file.py       # 本地文件上传（含 COS 上传签名）
```

## 快速开始

### 1. 获取凭证

前往 https://ima.qq.com/agent-interface 开通并获取 `Client ID` 与 `API Key`。

### 2. 配置凭证（二选一）

**环境变量：**

```bash
export IMA_CLIENT_ID="你的 Client ID"
export IMA_API_KEY="你的 API Key"
```

> 兼容别名：`IMA_OPENAPI_CLIENTID` / `IMA_OPENAPI_APIKEY`

**配置文件：**

```text
~/.config/ima/client_id      # 内容为 Client ID（纯文本，无换行）
~/.config/ima/api_key        # 内容为 API Key（纯文本，无换行）
```

Windows 下路径为 `%USERPROFILE%\.config\ima\`。

### 3. 调用

```bash
# 查看所有知识库
python scripts/ima_api.py openapi/wiki/v1/search_knowledge_base '{"query": "", "cursor": "", "limit": 20}'

# 浏览知识库根目录
python scripts/ima_api.py openapi/wiki/v1/get_knowledge_list '{"knowledge_base_id": "<kb_id>", "cursor": "", "limit": 50}'

# 上传本地文件
python scripts/upload_file.py --file "<本地文件绝对路径>" --knowledge-base-id "<kb_id>"
```

完整用法见 `SKILL.md`，接口字段见 `references/api.md`。

## 安全说明

- 仅允许访问 `https://ima.qq.com` 与腾讯云 COS（`*.myqcloud.com`）官方域名
- 上传前强制做类型与大小校验、重名检查，超限直接拒绝
- 凭证只在内存中使用，不写文件、不打日志

## 鸣谢（Acknowledgments）

感谢以下项目与工具（图标均取自官方站点 / CDN）：

<table>
  <tr>
    <td align="center" width="140">
      <a href="https://www.jetbrains.com/idea/">
        <img src="https://resources.jetbrains.com/storage/products/intellij-idea/img/meta/intellij-idea_logo_300x300.png" width="64" height="64" alt="IntelliJ IDEA" /><br />
        <sub><b>IntelliJ IDEA</b></sub>
      </a>
      <br />
      <sub>JetBrains 出品</sub>
    </td>
    <td align="center" width="140">
      <a href="https://www.jetbrains.com/pycharm/">
        <img src="https://resources.jetbrains.com/storage/products/pycharm/img/meta/pycharm_logo_300x300.png" width="64" height="64" alt="PyCharm" /><br />
        <sub><b>PyCharm</b></sub>
      </a>
      <br />
      <sub>JetBrains 出品</sub>
    </td>
  </tr>
</table>

| 项目 / 工具 | 贡献 | 许可证 / 说明 |
|---|---|---|
| [腾讯 IMA 知识库](https://ima.qq.com/) OpenAPI | 提供知识库检索、目录浏览、文件上传、笔记添加等接口，本项目是对其的轻量封装 | 平台服务，遵循 IMA 官方服务条款；需自行申请 `Client ID` / `API Key` |
| Python 标准库（`urllib` / `hmac` / `mimetypes` 等） | 承担全部网络、签名与文件处理能力，使技能保持零依赖 | Python Software Foundation License |
| [JetBrains](https://www.jetbrains.com/) | 提供 IntelliJ IDEA / PyCharm 等开发工具 | 商业授权（开源项目可申请免费许可证） |

> 本技能仅做接口封装，不存储用户凭证、不代理 IMA 账号体系。
> 贡献者名单：_（待补充，欢迎在 PR 中署名）_

## License

[MIT](LICENSE)
