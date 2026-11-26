"""从 cURL 或 Postman 集合里提取接口定义（不强依赖 OpenAPI）。"""
import json
import re
import shlex
from urllib.parse import parse_qs, urlparse

METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


def _infer_schema(obj) -> dict:
    """从示例 JSON 推断字段类型，给生成用例做参考。"""
    if not isinstance(obj, dict):
        return {}
    out = {}
    for key, val in list(obj.items())[:30]:
        if isinstance(val, bool):
            t = "boolean"
        elif isinstance(val, int):
            t = "integer"
        elif isinstance(val, float):
            t = "number"
        elif isinstance(val, (dict, list)):
            t = "object" if isinstance(val, dict) else "array"
        else:
            t = "string"
        out[key] = {"type": t, "required": True, "example": None, "enum": None}
    return out


def parse_curl(text: str) -> dict:
    """解析一条 curl，返回 {method, path, url, params, body, body_schema, headers, auth}。"""
    raw = text.strip()
    # 处理 Windows 的 ^ 续行和 shell 的 \ 续行
    raw = raw.replace("^\n", " ").replace("\\\n", " ")
    raw = re.sub(r"\r\n", "\n", raw).replace("\n", " ").strip()
    if raw.startswith("$"):
        raw = raw[1:].strip()
    if not raw.lower().startswith("curl"):
        raise ValueError("请粘贴以 curl 开头的命令")

    try:
        tokens = shlex.split(raw)
    except ValueError:
        tokens = raw.split()

    method = None
    url = None
    headers: dict[str, str] = {}
    data_parts: list[str] = []
    user = None

    i = 1
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("-X", "--request") and i + 1 < len(tokens):
            method = tokens[i + 1].upper()
            i += 2
            continue
        if tok in ("-H", "--header") and i + 1 < len(tokens):
            head = tokens[i + 1]
            if ":" in head:
                k, v = head.split(":", 1)
                headers[k.strip()] = v.strip()
            i += 2
            continue
        if tok in ("-d", "--data", "--data-raw", "--data-binary", "--data-ascii") and i + 1 < len(tokens):
            data_parts.append(tokens[i + 1])
            i += 2
            continue
        if tok in ("-u", "--user") and i + 1 < len(tokens):
            user = tokens[i + 1]
            i += 2
            continue
        if tok in ("--url",) and i + 1 < len(tokens):
            url = tokens[i + 1]
            i += 2
            continue
        if tok.startswith("-"):
            # 跳过未知选项；若是带值的选项，尽量跳掉值
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                i += 2
            else:
                i += 1
            continue
        if url is None:
            url = tok
        i += 1

    if not url:
        raise ValueError("没解析到 URL")

    parsed = urlparse(url)
    if not parsed.scheme:
        raise ValueError("URL 需要带 http:// 或 https://")

    params = {}
    for key, vals in parse_qs(parsed.query).items():
        params[key] = vals[0] if len(vals) == 1 else vals

    body = None
    body_schema = {}
    if data_parts:
        joined = " ".join(data_parts)
        try:
            body = json.loads(joined)
            body_schema = _infer_schema(body)
        except json.JSONDecodeError:
            body = None

    if method is None:
        method = "POST" if body is not None else "GET"

    auth = "none"
    if any(k.lower() == "authorization" for k in headers) or user:
        auth = "bearer"

    return {
        "method": method,
        "path": parsed.path or "/",
        "origin": f"{parsed.scheme}://{parsed.netloc}",
        "params": [{"name": k, "in": "query", "required": False, "schema": "string"} for k in params],
        "body_schema": body_schema,
        "response_schema": {},
        "auth_type": auth,
        "sample_params": params,
        "sample_body": body,
        "headers": headers,
    }


def parse_postman(collection: dict) -> list[dict]:
    """解析 Postman Collection v2.x，返回接口列表。"""
    out: list[dict] = []

    def walk(items):
        for item in items or []:
            if "item" in item:
                walk(item["item"])
                continue
            req = item.get("request") or {}
            url = req.get("url")
            if isinstance(url, dict):
                raw_url = url.get("raw", "")
            else:
                raw_url = url or ""
            if not raw_url:
                continue
            method = (req.get("method") or "GET").upper()
            if method not in METHODS:
                method = "GET"
            parsed = urlparse(raw_url if "://" in raw_url else f"http://{raw_url}")
            path = parsed.path or "/"

            headers = {
                h.get("key"): h.get("value")
                for h in (req.get("header") or [])
                if isinstance(h, dict) and h.get("key")
            }
            body = None
            body_schema = {}
            mode = ((req.get("body") or {}).get("mode") or "").lower()
            raw_body = (req.get("body") or {}).get("raw")
            if mode == "raw" and raw_body:
                try:
                    body = json.loads(raw_body)
                    body_schema = _infer_schema(body)
                except json.JSONDecodeError:
                    body = None

            out.append(
                {
                    "method": method,
                    "path": path,
                    "origin": f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else "",
                    "summary": (item.get("name") or "")[:280],
                    "params": [],
                    "body_schema": body_schema,
                    "response_schema": {},
                    "auth_type": "bearer"
                    if any(k.lower() == "authorization" for k in headers)
                    else "none",
                    "sample_params": {},
                    "sample_body": body,
                }
            )

    walk(collection.get("item") or [])
    return out
