"""用例生成：按 6 个维度让模型出用例，再校验、去重。"""
import hashlib
import json

from ..models import Case, Endpoint
from .llm import chat_json

SYSTEM = """你是资深接口测试工程师。根据给定的接口定义生成测试用例。
只输出 JSON 数组，不要解释。每个元素格式：
{
  "name": "用例名（简短中文）",
  "dimension": "normal|boundary|error|auth|idempotent|concurrent",
  "request": {"params": {}, "json": {}, "headers": {}},
  "expect": {"status": 200, "json_has": {}, "max_ms": 3000}
}
要求：
- 正常用例 1 条（dimension=normal）
- 边界 1 条（boundary：空串、超长、负数、边界值）
- 异常 1 条（error：缺必填、类型错）
- 鉴权 1 条，仅当接口需要鉴权：dimension=auth，并在 request 里加 "auth_bypass": true（表示故意不带凭证）
- 绝对不要生成 Authorization 头，凭证由系统注入
- 创建类接口默认期望 200（除非明确写了 201）
- 期望状态码：缺必填 400 或 422，未授权 401，不存在 404
- expect.json_has 只写必须存在的字段（可为空对象）
"""


def _endpoint_brief(ep: Endpoint) -> str:
    return json.dumps(
        {
            "method": ep.method,
            "path": ep.path,
            "summary": ep.summary,
            "auth_required": ep.auth_type != "none",
            "query_params": [p for p in (ep.params or []) if p.get("in") == "query"],
            "path_params": [p for p in (ep.params or []) if p.get("in") == "path"],
            "body_schema": ep.body_schema or {},
            "response_schema": ep.response_schema or {},
        },
        ensure_ascii=False,
    )


def fingerprint(ep: Endpoint, dimension: str, request: dict) -> str:
    raw = json.dumps(
        {"ep": ep.id, "dim": dimension, "req": request}, sort_keys=True, ensure_ascii=False
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:32]


def _normalize(ep: Endpoint, raw: dict) -> dict | None:
    """校验模型输出，补齐 method/path，过滤非法项。"""
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()[:180]
    dimension = str(raw.get("dimension") or "normal")
    if dimension not in {"normal", "boundary", "error", "auth", "idempotent", "concurrent"}:
        dimension = "normal"
    request = raw.get("request") if isinstance(raw.get("request"), dict) else {}
    expect = raw.get("expect") if isinstance(raw.get("expect"), dict) else {}
    if not name:
        return None
    status = expect.get("status", 200)
    if isinstance(status, list):
        status = status[0] if status else 200
    try:
        status = int(status)
    except (TypeError, ValueError):
        status = 200
    if not (100 <= status <= 599):
        status = 200

    return {
        "name": name,
        "dimension": dimension,
        "request": {
            "method": ep.method,
            "path": ep.path,
            "params": request.get("params") or {},
            "json": request.get("json") or {},
            "headers": request.get("headers") or {},
            "auth_bypass": bool(request.get("auth_bypass")),
        },
        "expect": {
            "status": status,
            "json_has": expect.get("json_has") or {},
            "max_ms": int(expect.get("max_ms") or 3000),
        },
    }


async def generate_cases(ep: Endpoint) -> list[dict]:
    """为一个接口生成用例（一次模型调用）。"""
    data = await chat_json(SYSTEM, _endpoint_brief(ep))
    if isinstance(data, dict):
        data = data.get("cases") or data.get("items") or []
    if not isinstance(data, list):
        return []

    out = []
    for raw in data[:6]:
        case = _normalize(ep, raw)
        if not case:
            continue
        # 公开接口不存在“未授权”场景，模型硬塞的鉴权用例直接丢掉（防误报）
        if case["dimension"] == "auth" and ep.auth_type == "none":
            continue
        out.append(case)
    return out


def save_cases(db, ep: Endpoint, cases: list[dict]) -> int:
    """写库并按 fingerprint 去重，返回新增条数。"""
    added = 0
    for case in cases:
        fp = fingerprint(ep, case["dimension"], case["request"])
        exists = db.query(Case).filter(Case.fingerprint == fp).first()
        if exists:
            continue
        db.add(
            Case(
                endpoint_id=ep.id,
                name=case["name"],
                dimension=case["dimension"],
                request=case["request"],
                expect=case["expect"],
                source="llm",
                fingerprint=fp,
            )
        )
        added += 1
    db.commit()
    return added
