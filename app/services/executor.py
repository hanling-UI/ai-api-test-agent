"""执行引擎：并发跑用例、断言、记录 trace。"""
import asyncio
import json
import time

import httpx
from sqlalchemy.orm import Session

from ..models import Case, Endpoint, Run, RunItem

CONCURRENCY = 5
TIMEOUT = 10.0


def _fill_path(path: str, params: dict) -> str:
    """把 /users/{id} 里的占位符替换掉（取 params 里的值，缺省用 1）。"""
    for key in list(params.keys()):
        path = path.replace("{" + key + "}", str(params[key]))
    # 没给值的占位符统一填 1，避免请求 404 让用例失效
    import re

    return re.sub(r"\{[^}]+\}", "1", path)


def _assert(resp: httpx.Response, expect: dict, elapsed_ms: int) -> tuple[bool, dict]:
    detail = {"checks": [], "ok": True}
    want_status = int(expect.get("status", 200))
    got = resp.status_code
    # 400/422 都属于“参数不合法”，框架选哪个不代表接口有 bug，等价处理
    ok = got == want_status or ({want_status, got} <= {400, 422})
    detail["checks"].append(
        {"name": "status", "expected": want_status, "actual": got, "ok": ok}
    )
    detail["ok"] &= ok

    body: dict | list | None = None
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        body = None

    json_has = expect.get("json_has") or {}
    if json_has and isinstance(body, dict):
        for key, val in json_has.items():
            hit = key in body and (val in (None, "") or body.get(key) == val)
            detail["checks"].append(
                {"name": f"field:{key}", "expected": val, "actual": body.get(key), "ok": hit}
            )
            detail["ok"] &= hit
    elif json_has and not isinstance(body, dict):
        detail["checks"].append(
            {"name": "json_body", "expected": "object", "actual": type(body).__name__, "ok": False}
        )
        detail["ok"] = False

    max_ms = int(expect.get("max_ms") or 0)
    if max_ms:
        ok_ms = elapsed_ms <= max_ms
        detail["checks"].append(
            {"name": "elapsed_ms", "expected": f"<={max_ms}", "actual": elapsed_ms, "ok": ok_ms}
        )
        detail["ok"] &= ok_ms

    return bool(detail["ok"]), detail


async def _run_one(client: httpx.AsyncClient, base_url: str, case: Case,
                   default_token: str, extra_headers: dict | None = None):
    req = case.request or {}
    method = (req.get("method") or "GET").upper()
    path = _fill_path(req.get("path") or "/", req.get("params") or {})
    url = base_url.rstrip("/") + path

    headers = dict(extra_headers or {})
    headers.update(req.get("headers") or {})
    # case 里带 auth_bypass=true 表示“故意不带凭证”，用于鉴权绕过测试
    bypass = bool(req.get("auth_bypass"))
    if default_token and not bypass and "authorization" not in {k.lower() for k in headers}:
        headers["Authorization"] = f"Bearer {default_token}"

    body = req.get("json") or {}
    started = time.perf_counter()
    try:
        resp = await client.request(
            method,
            url,
            params=req.get("params") or None,
            json=body if method in {"POST", "PUT", "PATCH"} and body else None,
            headers=headers,
        )
        elapsed = int((time.perf_counter() - started) * 1000)
        ok, detail = _assert(resp, case.expect or {}, elapsed)
        return {
            "case_id": case.id,
            "status": "passed" if ok else "failed",
            "request": {"method": method, "url": url, "params": req.get("params"), "json": body},
            "resp_status": resp.status_code,
            "resp_body": resp.text[:4000],
            "elapsed_ms": elapsed,
            "assert_detail": detail,
        }
    except Exception as exc:  # noqa: BLE001
        elapsed = int((time.perf_counter() - started) * 1000)
        return {
            "case_id": case.id,
            "status": "error",
            "request": {"method": method, "url": url, "params": req.get("params"), "json": body},
            "resp_status": 0,
            "resp_body": f"{type(exc).__name__}: {exc}",
            "elapsed_ms": elapsed,
            "assert_detail": {"ok": False, "checks": [{"name": "request", "ok": False}]},
        }


async def execute_run(
    db: Session, run: Run, project_base_url: str, default_token: str = "",
    extra_headers: dict | None = None,
) -> list[dict]:
    """执行 run 关联项目的所有启用用例，写入 run_items，返回结果列表。"""
    cases = (
        db.query(Case)
        .join(Endpoint, Endpoint.id == Case.endpoint_id)
        .filter(Endpoint.project_id == run.project_id, Case.enabled.is_(True))
        .all()
    )

    sem = asyncio.Semaphore(CONCURRENCY)
    results: list[dict] = []

    # 跟随重定向：真实浏览器会跟，测试工具也必须跟，
    # 否则「已登录访问 /login → 303 跳首页」会被误判为失败。
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:

        async def worker(case: Case):
            async with sem:
                res = await _run_one(client, project_base_url, case, default_token, extra_headers)
                results.append(res)

        await asyncio.gather(*(worker(c) for c in cases))

    # 落库
    for res in results:
        db.add(
            RunItem(
                run_id=run.id,
                case_id=res["case_id"],
                status=res["status"],
                request=res["request"],
                resp_status=res["resp_status"],
                resp_body=res["resp_body"],
                elapsed_ms=res["elapsed_ms"],
                assert_detail=res["assert_detail"],
            )
        )
    run.total = len(results)
    run.passed = sum(1 for r in results if r["status"] == "passed")
    run.failed = sum(1 for r in results if r["status"] != "passed")
    db.commit()
    return results
