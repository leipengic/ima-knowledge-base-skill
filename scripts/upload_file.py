#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload_file.py — 将本地文件上传到 IMA 知识库。

完整流程：前置检查 → 重名检查 → create_media → COS 上传 → add_knowledge。

安全设计：
- 仅访问 ima.qq.com 与腾讯云 COS（*.myqcloud.com）官方域名；
- 上传前强制做类型与大小校验（preflight），超限直接拒绝；
- 上传前强制做重名检查，同名时由调用方决策（保留两者 / 跳过 / 强制覆盖名）；
- 本脚本不做任何本地文件删除、系统修改操作。

用法：
    python upload_file.py --file <本地文件路径> --knowledge-base-id <kb_id>
                          [--folder-id <folder_id>] [--title <标题>]
                          [--keep-both | --skip-if-exists | --force]

参数说明：
    --file              必填，本地文件绝对路径
    --knowledge-base-id 必填，目标知识库 ID（用 ima_api.py 查得）
    --folder-id         可选，目标文件夹 ID（省略则根目录）
    --title             可选，知识库中显示标题（默认与文件名一致）
    --keep-both         重名时保留两者（自动追加时间戳）
    --skip-if-exists    重名时跳过上传
    --force             跳过重名检查直接上传（不推荐）

退出码：0=成功，1=程序错误，2=API 返回业务错误。
"""

import argparse
import hashlib
import hmac
import json
import mimetypes
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ima_api import ImaError, load_credentials, post_json  # noqa: E402

# 支持的文件类型（扩展名 -> (media_type, mime, 大小上限MB)）
SUPPORTED_TYPES = {
    ".pdf": (1, "application/pdf", 200),
    ".doc": (3, "application/msword", 200),
    ".docx": (3, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 200),
    ".ppt": (4, "application/vnd.ms-powerpoint", 200),
    ".pptx": (4, "application/vnd.openxmlformats-officedocument.presentationml.presentation", 200),
    ".xls": (5, "application/vnd.ms-excel", 10),
    ".xlsx": (5, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 10),
    ".csv": (5, "text/csv", 10),
    ".md": (7, "text/markdown", 10),
    ".markdown": (7, "text/markdown", 10),
    ".png": (9, "image/png", 30),
    ".jpg": (9, "image/jpeg", 30),
    ".jpeg": (9, "image/jpeg", 30),
    ".webp": (9, "image/webp", 30),
    ".txt": (13, "text/plain", 10),
    ".xmind": (14, "application/vnd.xmind.workbook", 10),
    ".mp3": (15, "audio/mpeg", 200),
    ".m4a": (15, "audio/x-m4a", 200),
    ".wav": (15, "audio/wav", 200),
    ".aac": (15, "audio/aac", 200),
}

MB = 1024 * 1024


def detect_type(file_path: Path) -> tuple[int, str, int]:
    """返回 (media_type, content_type, max_size)。不支持的类型抛 ImaError。"""
    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_TYPES:
        raise ImaError(-100, f"不支持的文件类型: {ext or '(无扩展名)'}。支持: {', '.join(sorted(SUPPORTED_TYPES))}")
    return SUPPORTED_TYPES[ext]


def hmac_sha1(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha1).digest()


def sha1_hex(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def build_cos_authorization(
    secret_id: str,
    secret_key: str,
    method: str,
    pathname: str,
    headers: dict[str, str],
    start_time: str,
    expired_time: str,
) -> str:
    """构造腾讯云 COS 签名（参考官方文档 https://cloud.tencent.com/document/product/436/7778）。"""
    key_time = f"{start_time};{expired_time}"
    sign_key = hmac_sha1(secret_key.encode("utf-8"), key_time.encode("utf-8")).hex()
    header_keys = sorted(headers.keys())
    http_headers = "&".join(
        f"{k.lower()}={urllib.parse.quote(str(headers[k]), safe='')}" for k in header_keys
    )
    http_string = f"{method.lower()}\n{pathname}\n\n{http_headers}\n"
    string_to_sign = f"sha1\n{key_time}\n{sha1_hex(http_string.encode('utf-8'))}\n"
    signature = hmac_sha1(sign_key.encode("utf-8"), string_to_sign.encode("utf-8")).hex()
    header_list = ";".join(k.lower() for k in header_keys)
    return (
        f"q-sign-algorithm=sha1&q-ak={secret_id}&q-sign-time={key_time}"
        f"&q-key-time={key_time}&q-header-list={header_list}&q-url-param-list=&q-signature={signature}"
    )


def upload_to_cos(file_path: Path, credential: dict, content_type: str, timeout_ms: int = 300000) -> None:
    """将文件上传到腾讯云 COS（PUT Object）。credential 为 create_media 返回的 cos_credential。"""
    file_content = file_path.read_bytes()
    bucket = credential["bucket_name"]
    region = credential["region"]
    cos_key = credential["cos_key"]
    token = credential["token"]
    secret_id = credential["secret_id"]
    secret_key = credential["secret_key"]
    start_time = str(credential.get("start_time") or int(time.time()))
    expired_time = str(credential.get("expired_time") or int(time.time()) + 3600)

    hostname = f"{bucket}.cos.{region}.myqcloud.com"
    pathname = f"/{cos_key}"
    sign_headers = {
        "content-length": str(len(file_content)),
        "host": hostname,
    }
    authorization = build_cos_authorization(
        secret_id, secret_key, "PUT", pathname, sign_headers, start_time, expired_time
    )
    url = f"https://{hostname}{pathname}"
    request = urllib.request.Request(
        url,
        data=file_content,
        method="PUT",
        headers={
            "Content-Type": content_type,
            "Content-Length": str(len(file_content)),
            "Authorization": authorization,
            "x-cos-security-token": token,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_ms / 1000) as resp:
            if not (200 <= resp.status < 300):
                raise ImaError(-100, f"COS 上传失败 (HTTP {resp.status})")
    except urllib.error.HTTPError as e:
        raise ImaError(-100, f"COS 上传失败 (HTTP {e.code}): {e.read().decode('utf-8', errors='replace')[:500]}")
    except urllib.error.URLError as e:
        raise ImaError(-100, f"COS 上传网络错误: {e.reason}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="上传本地文件到 IMA 知识库")
    parser.add_argument("--file", required=True, help="本地文件绝对路径")
    parser.add_argument("--knowledge-base-id", required=True, help="目标知识库 ID")
    parser.add_argument("--folder-id", default=None, help="目标文件夹 ID（默认根目录）")
    parser.add_argument("--title", default=None, help="知识库中显示标题（默认与文件名一致）")
    parser.add_argument("--keep-both", action="store_true", help="重名时保留两者（追加时间戳）")
    parser.add_argument("--skip-if-exists", action="store_true", help="重名时跳过上传")
    parser.add_argument("--force", action="store_true", help="跳过重名检查（不推荐）")
    args = parser.parse_args(argv)

    file_path = Path(args.file)
    if not file_path.is_file():
        print(json.dumps({"code": -100, "msg": f"文件不存在: {file_path}"}, ensure_ascii=False))
        return 1

    file_name = file_path.name
    title = args.title or file_name
    file_size = file_path.stat().st_size

    # Step 1: 前置检查（类型 + 大小）
    try:
        media_type, content_type, max_mb = detect_type(file_path)
    except ImaError as e:
        print(json.dumps({"code": e.code, "msg": e.msg}, ensure_ascii=False))
        return 1
    if file_size > max_mb * MB:
        print(json.dumps({"code": -100, "msg": f"文件超过大小限制（{max_mb}MB）: {file_name}"}, ensure_ascii=False))
        return 1

    kb_id = args.knowledge_base_id

    # Step 2: 重名检查（除非 --force）
    if not args.force:
        check_body = {
            "params": [{"name": file_name, "media_type": media_type}],
            "knowledge_base_id": kb_id,
        }
        if args.folder_id:
            check_body["folder_id"] = args.folder_id
        check_resp = post_json("openapi/wiki/v1/check_repeated_names", check_body)
        if check_resp.get("code") != 0:
            print(json.dumps(check_resp, ensure_ascii=False))
            return 2
        results = (check_resp.get("data") or {}).get("results") or []
        is_repeated = any(r.get("is_repeated") for r in results)
        if is_repeated:
            if args.skip_if_exists:
                print(json.dumps({"code": 0, "msg": f"已存在同名文件，已跳过: {file_name}"}, ensure_ascii=False))
                return 0
            if args.keep_both:
                stem, ext = os.path.splitext(file_name)
                file_name = f"{stem}_{time.strftime('%Y%m%d%H%M%S')}{ext}"
                title = args.title or file_name
            else:
                print(json.dumps(
                    {"code": -100, "msg": f"知识库中已存在同名文件: {file_name}。请使用 --keep-both 保留两者或 --skip-if-exists 跳过。"},
                    ensure_ascii=False))
                return 1

    # Step 3: create_media
    create_body = {
        "file_name": file_name,
        "file_size": file_size,
        "content_type": content_type,
        "knowledge_base_id": kb_id,
        "file_ext": file_path.suffix.lstrip(".").lower(),
    }
    create_resp = post_json("openapi/wiki/v1/create_media", create_body)
    if create_resp.get("code") != 0:
        print(json.dumps(create_resp, ensure_ascii=False))
        return 2
    data = create_resp.get("data") or {}
    media_id = data.get("media_id")
    credential = data.get("cos_credential") or {}
    if not media_id or not credential:
        print(json.dumps({"code": -100, "msg": "create_media 返回缺少 media_id 或 cos_credential"}, ensure_ascii=False))
        return 1

    # Step 4: COS 上传
    try:
        upload_to_cos(file_path, credential, content_type)
    except ImaError as e:
        print(json.dumps({"code": e.code, "msg": e.msg}, ensure_ascii=False))
        return 1

    # Step 5: add_knowledge
    add_body = {
        "media_type": media_type,
        "media_id": media_id,
        "title": title,
        "knowledge_base_id": kb_id,
        "file_info": {
            "cos_key": credential.get("cos_key", ""),
            "file_size": file_size,
            "file_name": file_name,
        },
    }
    if args.folder_id:
        add_body["folder_id"] = args.folder_id
    add_resp = post_json("openapi/wiki/v1/add_knowledge", add_body)
    print(json.dumps(add_resp, ensure_ascii=False))
    return 0 if add_resp.get("code") == 0 else 2


if __name__ == "__main__":
    sys.exit(main())

