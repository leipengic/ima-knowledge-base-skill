# ima-knowledge-base-skill

连接腾讯 IMA 知识库（https://ima.qq.com）的 Agent 技能包，提供一套基于 Python 标准库的知识库**读取**与**写入**能力，包括知识库搜索/浏览、本地文件上传、网页/微信文章导入、笔记添加、媒体原文读取等。

## 特性

- 零依赖：仅使用 Python 3.8+ 标准库，无需第三方包，跨 Windows / macOS / Linux
- 安全优先：仅访问 `ima.qq.com` 与腾讯云 COS 官方域名，内置 SSRF 防护；凭证只从环境变量或配置文件读取，绝不写入磁盘、绝不输出到日志
- 完整封装：覆盖知识库搜索、目录浏览、站内搜索、媒体原文、重名检查、文件上传、URL 导入、笔记添加等接口

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

## License

[MIT](LICENSE)
