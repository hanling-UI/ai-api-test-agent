"""缺陷单生成：把失败结果整理成可提交的缺陷。"""
from ..models import Case, Endpoint, RunItem


def build_issue(project_id: int, run_id: int, item: RunItem, case: Case, ep: Endpoint,
                verdict: str, reason: str, severity: str, actor_id: int) -> dict:
    req = item.request or {}
    method = req.get("method", ep.method)
    url = req.get("url", "")
    body = req.get("json")
    params = req.get("params")

    curl = f"curl -X {method} '{url}'"
    if params:
        curl += " -G " + " ".join(f"--data-urlencode '{k}={v}'" for k, v in params.items())
    if body:
        curl += f" -H 'Content-Type: application/json' -d '{body}'"

    want = (case.expect or {}).get("status")
    title = f"[{ep.method} {ep.path}] {case.name}：期望 {want}，实际 {item.resp_status}"

    steps = (
        f"1. 请求：{method} {url}\n"
        f"2. 参数：{params or '-'}\n"
        f"3. 请求体：{body or '-'}\n"
        f"4. 实际响应码：{item.resp_status}\n"
        f"5. 响应内容：{(item.resp_body or '')[:500]}"
    )

    return {
        "project_id": project_id,
        "endpoint_id": ep.id,
        "run_id": run_id,
        "run_item_id": item.id,
        "title": title[:280],
        "severity": severity,
        "steps": steps,
        "expected": f"HTTP {want}",
        "actual": f"HTTP {item.resp_status}（{reason}）",
        "curl": curl,
        "status": "draft",
        "created_by": actor_id,
    }
