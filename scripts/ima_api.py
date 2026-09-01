#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ima_api.py — IMA OpenAPI 统一调用客户端（知识库模块 openapi/wiki/v1）。

用途：让 Marvis 连接腾讯 IMA 知识库并执行读取/写入操作。
所有请求均为 HTTPS POST + JSON Body，凭证通过 Header 传递。

安全设计：
- 仅访问 https://ima.qq.com 官方域名；
- 凭证只从环境变量或 ~/.config/ima/ 读取，绝不写入磁盘、绝不输出到日志；
- 本脚本为只读封装，不执行任何文件删除、系统修改类操作。

用法：
    python ima_api.py <api_path> '<json_body>'
示例：
    python ima_api.py openapi/wiki/v1/search_knowledge_base '{"query": "", "cursor": "", "limit": 20}'
    python ima_api.py openapi/wiki/v1/get_knowledge_list '{"knowledge_base_id": "<kb_id>", "cursor": "", "limit": 50}'

凭证优先级（从高到低）：
1. 环境变量 IMA_CLIENT_ID / IMA_API_KEY
2. 环境变量 IMA_OPENAPI_CLIENTID / IMA_OPENAPI_APIKEY
3. 文件 ~/.config/ima/client_id 与 ~/.config/ima/api_key（Windows: %USERPROFILE%\\.config\\ima\\）
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = "https://ima.qq.com"
DEFAULT_TIMEOUT = 30  # 秒

# 仅允许访问 IMA 官方域名，防止 SSRF / 任意地址请求
ALLOWED_HOSTS = {"ima.qq.com"}


class ImaError(Exception):
    """IMA 调用异常。"""

    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code
        self.msg = msg


def _read_file_safe(path: Path) -> str:
    """读取凭证文件，失败时返回空字符串。"""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def load_credentials() -> tuple[str, str]:
    """按优先级加载凭证（client_id / api_key）。"""
    client_id = (
        os.environ.get("IMA_CLIENT_ID")
        or os.environ.get("IMA_OPENAPI_CLIENTID")
        or _read_file_safe(Path.home() / ".config" / "ima" / "client_id")
    )
    api_key = (
        os.environ.get("IMA_API_KEY")
        or os.environ.get("IMA_OPENAPI_APIKEY")
        or _read_file_safe(Path.home() / ".config" / "ima" / "api_key")
    )
    if not client_id or not api_key:
        raise ImaError(
            -100,
            "未找到 IMA 凭证（client_id / api_key）。请到 https://ima.qq.com/agent-interface 获取，"
            "并配置环境变量 IMA_CLIENT_ID / IMA_API_KEY，或将凭证写入 ~/.config/ima/client_id 与 ~/.config/ima/api_key。",
        )
    return client_id, api_key


def post_json(api_path: str, body: dict, client_id: str = None, api_key: str = None) -> dict:
    """向 IMA OpenAPI 发起 POST 请求并解析 JSON 响应。"""
    if client_id is None or api_key is None:
        client_id, api_key = load_credentials()

    # SSRF 防护：仅允许 HTTPS 协议与 ima.qq.com 官方域名
    url = f"{BASE_URL}/{api_path.lstrip('/')}"
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ImaError(-100, f"不允许访问非 IMA 官方地址: {parsed.hostname or url}")

    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "ima-openapi-clientid": client_id,
            "ima-openapi-apikey": api_key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise ImaError(e.code, f"HTTP {e.code}: {raw[:500]}")
    except urllib.error.URLError as e:
        raise ImaError(-100, f"网络错误: {e.reason}")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise ImaError(-100, f"响应不是合法 JSON: {raw[:500]}")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("用法: python ima_api.py <api_path> '<json_body>'", file=sys.stderr)
        return 1

    api_path = argv[0]
    try:
        body = json.loads(argv[1]) if len(argv) > 1 and argv[1].strip() else {}
    except json.JSONDecodeError:
        print("请求 body 不是合法 JSON", file=sys.stderr)
        return 1

    try:
        result = post_json(api_path, body)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("code") == 0 else 2
    except ImaError as e:
        print(json.dumps({"code": e.code, "msg": e.msg}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

