---
name: ima-knowledge-base
description: >-
  连接腾讯 IMA 知识库并执行读取/写入操作。支持搜索/浏览知识库、上传本地文件、
  导入网页/微信文章、添加笔记、读取媒体原文。当用户提到 ima、ima知识库、腾讯ima、
  知识库搜索、知识库上传、知识库导入、添加文件到知识库、查询知识库内容等需求时使用。
license: MIT
---

# IMA 知识库操作

连接腾讯 IMA（https://ima.qq.com）开放知识库接口，实现知识库的**读取**与**写入**操作。

- API Base: `https://ima.qq.com/openapi/wiki/v1`
- 凭证：环境变量 `IMA_CLIENT_ID` / `IMA_API_KEY`（兼容 `IMA_OPENAPI_CLIENTID` / `IMA_OPENAPI_APIKEY`），或文件 `~/.config/ima/client_id` 与 `~/.config/ima/api_key`
- 完整接口字段见 `references/api.md`

## 使用前提

1. 用户需已在 https://ima.qq.com/agent-interface 开通并获取 Client ID 与 API Key。
2. 凭证配置方式（二选一）：
   - 环境变量：`IMA_CLIENT_ID`、`IMA_API_KEY`（兼容 `IMA_OPENAPI_CLIENTID` / `IMA_OPENAPI_APIKEY`）
   - 文件：`%USERPROFILE%\.config\ima\client_id`、`%USERPROFILE%\.config\ima\api_key`（内容为纯文本，无换行）
3. 若凭证缺失，脚本会返回提示，Agent 须如实告知用户配置凭证，不得编造或猜测。

## 脚本用法

本 skill 提供两个 Python 脚本（运行于 Windows / macOS / Linux，依赖 Python 3.8+ 标准库，无需第三方包）：

### ima_api.py — 通用 API 调用

```bash
python <skill_dir>/scripts/ima_api.py <api_path> '<json_body>'
```

示例：

```bash
# 查看所有知识库
python <skill_dir>/scripts/ima_api.py openapi/wiki/v1/search_knowledge_base '{"query": "", "cursor": "", "limit": 20}'

# 按名称搜索知识库
python <skill_dir>/scripts/ima_api.py openapi/wiki/v1/search_knowledge_base '{"query": "产品文档", "cursor": "", "limit": 20}'

# 获取知识库详情
python <skill_dir>/scripts/ima_api.py openapi/wiki/v1/get_knowledge_base '{"ids": ["<kb_id>"]}'

# 浏览知识库根目录
python <skill_dir>/scripts/ima_api.py openapi/wiki/v1/get_knowledge_list '{"knowledge_base_id": "<kb_id>", "cursor": "", "limit": 50}'

# 浏览子文件夹
python <skill_dir>/scripts/ima_api.py openapi/wiki/v1/get_knowledge_list '{"knowledge_base_id": "<kb_id>", "folder_id": "<folder_id>", "cursor": "", "limit": 50}'

# 知识库内搜索
python <skill_dir>/scripts/ima_api.py openapi/wiki/v1/search_knowledge '{"query": "排期", "knowledge_base_id": "<kb_id>", "cursor": ""}'

# 获取媒体原文
python <skill_dir>/scripts/ima_api.py openapi/wiki/v1/get_media_info '{"media_id": "<media_id>"}'

# 导入网页/微信文章
python <skill_dir>/scripts/ima_api.py openapi/wiki/v1/import_urls '{"knowledge_base_id": "<kb_id>", "folder_id": "<kb_id>", "urls": ["https://example.com/article"]}'
```

返回统一为 JSON：`{"code": 0, "msg": "...", "data": {...}}`。`code≠0` 时直接把 `msg` 呈现给用户。

### upload_file.py — 上传本地文件

```bash
python <skill_dir>/scripts/upload_file.py \
  --file "<本地文件绝对路径>" \
  --knowledge-base-id "<kb_id>" \
  [--folder-id "<folder_id>"] \
  [--keep-both | --skip-if-exists | --force]
```

- 自动完成：类型/大小校验 → 重名检查 → 创建媒体 → COS 上传 → 添加到知识库
- 重名默认拦截；`--keep-both` 追加时间戳保留两者；`--skip-if-exists` 跳过
- 音频时长超过 2 小时不支持（官方限制）

## 接口决策表

| 用户意图 | 调用方式 |
| --- | --- |
| 查看自己有哪些知识库 | `search_knowledge_base`（query 传空串） |
| 按名称找知识库 | `search_knowledge_base` |
| 浏览知识库内容/文件夹 | `get_knowledge_list`（可传 folder_id） |
| 在知识库内搜索 | `search_knowledge` |
| 查看原文/分析原文/导出原文 | `get_media_info` |
| 添加内容但未指定知识库 | `get_addable_knowledge_base_list` → 让用户选择 |
| 上传本地文件 | `upload_file.py` |
| 添加网页/微信文章 | `import_urls` |
| 添加笔记 | `add_knowledge`（media_type=11） |

**绝不要**在用户已明确指定知识库名称时调用 `get_addable_knowledge_base_list`。

## 文件夹操作

- 操作根目录时省略 `folder_id`；`import_urls` 的 `folder_id` 必填时传 `knowledge_base_id` 的值
- 用户只给文件夹名时：用 `search_knowledge` 按名称搜，或 `get_knowledge_list` 逐级浏览，从结果取 `folder_id`
- 文件夹条目特征：返回中的 `folder_id` 以 `folder_` 开头

## 安全约束

1. **文件上传安全门**：
   - 不支持的类型（视频、B站/YouTube URL、file:// 等）直接拒绝，告知用户使用 IMA 桌面客户端，**不得询问"是否仍要尝试"**
   - 上传前必须重名检查；不支持"替换"语义
   - 标题必须等于原文件名（含扩展名），不得改名/缩写/翻译
2. **隐藏内部 ID**：面向用户展示时用知识库名称、文件标题、文件夹名称，**禁止暴露** `knowledge_base_id` / `media_id` / `folder_id`
3. **只读不越权**：脚本仅访问 `ima.qq.com` 与腾讯云 COS 官方域名，不做本地文件删除、不修改系统配置
4. **凭证保护**：凭证只在内存中使用，不写入任何文件，不在日志中输出
5. **视频/音频**：Bilibili/YouTube/视频类 URL 与本地 HTML 不支持通过 skill 添加，提示用户用 IMA 桌面端
6. **大小限制**：Excel/TXT/Xmind/Markdown ≤10MB，图片 ≤30MB，PDF/Word/PPT/音频 ≤200MB

## 分页规范

所有列表接口游标分页：首次 `cursor=""` → 检查 `is_end` → 用 `next_cursor` 翻页 → `is_end=true` 停止。

## 用户体验

- 不逐步暴露内部操作（"正在创建媒体…正在上传 COS…"），只报告：
  - 上传：`"正在上传 report.pdf…"` → `"已添加到知识库「产品文档库」"`
  - 导入：`"正在添加…"` → `"已添加到「产品文档库」"`
  - 失败时展示 `msg`
- 批量操作汇总结果
- 展示知识库/内容列表时使用结构化列表（名称、描述、文件数等）
