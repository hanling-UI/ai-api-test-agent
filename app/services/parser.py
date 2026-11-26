"""OpenAPI 解析：把 spec 变成可测的接口清单。"""
from typing import Any

METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def _resolve_ref(spec: dict, node: Any) -> Any:
    """只处理一层 $ref（够用），避免递归爆栈。"""
    if isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"].lstrip("#/").split("/")
        cur: Any = spec
        for part in ref:
            if not isinstance(cur, dict):
                return {}
            cur = cur.get(part, {})
        return cur
    return node


def _schema_summary(schema: dict, spec: dict) -> dict:
    """把 JSON Schema 压成“字段名 -> 类型/是否必填”的摘要，喂给模型。"""
    schema = _resolve_ref(spec, schema) or {}
    props = schema.get("properties", {}) or {}
    required = set(schema.get("required", []) or [])
    out = {}
    for name, prop in list(props.items())[:20]:
        prop = _resolve_ref(spec, prop) or {}
        out[name] = {
            "type": prop.get("type", "any"),
            "required": name in required,
            "example": prop.get("example"),
            "enum": prop.get("enum"),
        }
    return out


def parse_openapi(spec: dict) -> list[dict]:
    """返回 [{method, path, summary, params, body_schema, response_schema, auth_type}]。"""
    endpoints: list[dict] = []
    security_defined = bool(spec.get("components", {}).get("securitySchemes"))

    for path, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method, op in item.items():
            if method.lower() not in METHODS or not isinstance(op, dict):
                continue

            params = []
            for raw in (op.get("parameters") or []) + (item.get("parameters") or []):
                raw = _resolve_ref(spec, raw) or {}
                params.append(
                    {
                        "name": raw.get("name"),
                        "in": raw.get("in"),
                        "required": bool(raw.get("required")),
                        "schema": (raw.get("schema") or {}).get("type", "string"),
                    }
                )

            body_schema = {}
            rb = op.get("requestBody") or {}
            content = (rb.get("content") or {}) if isinstance(rb, dict) else {}
            for media, media_obj in content.items():
                if "json" in media:
                    body_schema = _schema_summary(
                        (media_obj or {}).get("schema", {}), spec
                    )
                    break

            response_schema = {}
            responses = op.get("responses") or {}
            for code in ("200", "201", 200, 201):
                if code in responses:
                    content = (responses[code] or {}).get("content") or {}
                    for media, media_obj in content.items():
                        if "json" in media:
                            response_schema = _schema_summary(
                                (media_obj or {}).get("schema", {}), spec
                            )
                            break
                    break

            auth_type = "none"
            if op.get("security") or (security_defined and not op.get("security")):
                auth_type = "bearer"

            endpoints.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "summary": (op.get("summary") or op.get("operationId") or "")[:280],
                    "params": params,
                    "body_schema": body_schema,
                    "response_schema": response_schema,
                    "auth_type": auth_type,
                }
            )

    return endpoints
