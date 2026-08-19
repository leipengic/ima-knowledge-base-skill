# IMA 知识库 API 参考

## 服务信息

- **Base URL**: `https://ima.qq.com`
- **Base Path**: `/openapi/wiki/v1`
- **协议**: HTTP POST + JSON Body

## 认证

所有请求必须携带以下 Header（由 `scripts/ima_api.py` 自动附加）：

| Header | 说明 |
| --- | --- |
| `ima-openapi-clientid` | Client ID |
| `ima-openapi-apikey` | API Key |
| `Content-Type` | `application/json` |

凭证来源（优先级从高到低）：
1. 环境变量 `IMA_CLIENT_ID` / `IMA_API_KEY`
2. 环境变量 `IMA_OPENAPI_CLIENTID` / `IMA_OPENAPI_APIKEY`
3. 文件 `~/.config/ima/client_id` 与 `~/.config/ima/api_key`（Windows: `%USERPROFILE%\.config\ima\`）

获取方式：https://ima.qq.com/agent-interface

## 统一响应格式

```json
{ "code": 0, "msg": "成功", "data": { ... } }
```

- `code=0`：成功，从 `data` 提取业务字段
- `code≠0`：失败，直接将 `msg` 展示给用户

## 接口总览

| 接口 | 用途 |
| --- | --- |
| `search_knowledge_base` | 按名称搜索知识库；`query` 传空串返回全部知识库 |
| `get_knowledge_base` | 获取知识库详情（ids 数组，1-20 个） |
| `get_addable_knowledge_base_list` | 获取当前用户有权限添加内容的知识库列表 |
| `get_knowledge_list` | 浏览知识库内容（支持文件夹） |
| `search_knowledge` | 在知识库内搜索 |
| `get_media_info` | 获取媒体原文访问信息 |
| `check_repeated_names` | 上传前检查重名（仅文件类） |
| `create_media` | 创建媒体，获取 COS 上传凭证 |
| `add_knowledge` | 添加知识（文件/网页/笔记） |
| `import_urls` | 批量导入网页/微信文章 URL |

## 接口详情

### search_knowledge_base

```json
{ "query": "", "cursor": "", "limit": 20 }
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `query` | string | 是 | 搜索关键词，空串返回全部 |
| `cursor` | string | 是 | 游标，首次传空串 |
| `limit` | uint64 | 是 | 1-20 |

返回：`info_list[]`（`id`、`name`、`cover_url`）、`is_end`、`next_cursor`

### get_knowledge_base

```json
{ "ids": ["kb_id"] }
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `ids` | string[] | 是 | 知识库 ID 列表（1-20 个，不重复） |

返回：`infos`（map，含 `name`、`description`、`recommended_questions`、`cover_url`）

### get_addable_knowledge_base_list

```json
{ "cursor": "", "limit": 50 }
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `cursor` | string | 是 | 游标，首次传空串 |
| `limit` | uint64 | 是 | 1-50 |

返回：`addable_knowledge_base_list[]`（`id`、`name`）、`next_cursor`、`is_end`

### get_knowledge_list

```json
{ "knowledge_base_id": "kb_id", "cursor": "", "limit": 50, "folder_id": "folder_xxx" }
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `knowledge_base_id` | string | 是 | 知识库 ID |
| `cursor` | string | 是 | 游标，首次传空串 |
| `limit` | uint64 | 是 | 1-50 |
| `folder_id` | string | 否 | 文件夹 ID，省略则根目录 |

返回：`knowledge_list[]`（文件：`media_id`、`title`、`parent_folder_id`）、文件夹（`folder_id`、`name`、`file_number`、`folder_number`）、`current_path`（面包屑）、`is_end`、`next_cursor`

### search_knowledge

```json
{ "query": "关键词", "knowledge_base_id": "kb_id", "cursor": "" }
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `query` | string | 是 | 搜索关键词 |
| `knowledge_base_id` | string | 是 | 知识库 ID |
| `cursor` | string | 是 | 游标 |

返回：`info_list[]`（`media_id`、`title`、`parent_folder_id`、`highlight_content`）、`is_end`、`next_cursor`

### get_media_info

```json
{ "media_id": "media_id" }
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `media_id` | string | 是 | 媒体 ID |

返回：`media_type`、`url_info`（`url`、`headers`）、`notebook_ext_info`（`notebook_id`，仅笔记）

处理分支：
- `media_type=11` 且 `notebook_ext_info.notebook_id` 存在 → 笔记，按 note_id 获取内容
- `url_info.url` 非空 → 用 url + headers 请求原文
- 否则/请求失败 → 提示「请使用 IMA 客户端查看原文」
- 下载时在 URL 后追加 `response-content-type=application/octet-stream&response-content-disposition=attachment;filename="<name>"`

### check_repeated_names

```json
{
  "params": [{"name": "报告.pdf", "media_type": 1}],
  "knowledge_base_id": "kb_id",
  "folder_id": "folder_xxx"
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `params` | array | 是 | 1-2000 个 `{name, media_type}` |
| `knowledge_base_id` | string | 是 | 知识库 ID |
| `folder_id` | string | 否 | 文件夹 ID |

返回：`results[]`（`name`、`is_repeated`）

### create_media

```json
{
  "file_name": "报告.pdf",
  "file_size": 102400,
  "content_type": "application/pdf",
  "knowledge_base_id": "kb_id",
  "file_ext": "pdf"
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file_name` | string | 是 | 文件名称 |
| `file_size` | uint64 | 是 | 字节数 |
| `content_type` | string | 是 | MIME 类型 |
| `knowledge_base_id` | string | 是 | 知识库 ID |
| `file_ext` | string | 是 | 后缀名（无点号） |

返回：`media_id`、`cos_credential`（`token`、`secret_id`、`secret_key`、`bucket_name`、`region`、`cos_key` 等）

### add_knowledge

文件上传时：

```json
{
  "media_type": 1,
  "media_id": "media_id",
  "title": "报告.pdf",
  "knowledge_base_id": "kb_id",
  "folder_id": "folder_xxx",
  "file_info": {"cos_key": "xxx", "file_size": 102400, "file_name": "报告.pdf"}
}
```

添加网页时：

```json
{
  "media_type": 2,
  "web_info": {"content_id": "https://example.com/article"},
  "title": "文章标题",
  "knowledge_base_id": "kb_id"
}
```

添加笔记时：

```json
{
  "media_type": 11,
  "note_info": {"content_id": "note_id"},
  "title": "笔记标题",
  "knowledge_base_id": "kb_id"
}
```

### import_urls

```json
{
  "knowledge_base_id": "kb_id",
  "folder_id": "kb_id",
  "urls": ["https://example.com/article", "https://mp.weixin.qq.com/s/xxx"]
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `knowledge_base_id` | string | 是 | 知识库 ID |
| `folder_id` | string | 是 | 文件夹 ID（根目录传 knowledge_base_id 的值） |
| `urls` | string[] | 是 | 1-10 个 URL |

返回：`results`（map：url → `{url, ret_code, media_id}`）

## MediaType 枚举

| 值 | 类型 | 说明 |
| --- | --- | --- |
| 1 | PDF | `application/pdf` |
| 2 | 网页 | `web_info.content_id=<url>` |
| 3 | Word | doc/docx |
| 4 | PPT | ppt/pptx |
| 5 | Excel | xls/xlsx/csv |
| 6 | 微信公众号文章 | mp.weixin.qq.com/s |
| 7 | Markdown | md/markdown |
| 9 | 图片 | png/jpeg/webp |
| 11 | 笔记 | `note_info.content_id=<note_id>` |
| 13 | TXT | `text/plain` |
| 14 | Xmind | xmind |
| 15 | 录音 | mp3/m4a/wav/aac |
| 16 | 视频解析 | 不支持通过 skill 添加 |

## 文件大小限制

| 类型 | media_type | 上限 |
| --- | --- | --- |
| Excel/TXT/Xmind/Markdown | 5/13/14/7 | 10 MB |
| 图片 | 9 | 30 MB |
| PDF/Word/PPT/音频等 | 1/3/4/15 | 200 MB |

## 游标翻页

1. 首次 `cursor=""`；2. `is_end=false` 时用 `next_cursor` 继续；3. `is_end=true` 停止。

## 错误码

| 错误码 | 说明 |
| --- | --- |
| 0 | 成功 |
| 110001 | 参数非法 |
| 110002 | 配置非法 |
| 110010 | 下游网络错误（可重试） |
| 110011 | 下游逻辑错误 |
| 110012 | 接口无效 |
| 110013 | 客户端取消 |
| 110020 | 安全打击 |
| 110021 | 请求频控 |
| 110030 | 无权限 |
