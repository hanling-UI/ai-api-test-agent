"""失败归因：区分「接口 bug / 用例写错 / 环境问题」。

策略：**规则优先**（确定性、可解释），模型只负责把原因写成人话。
这样即使模型抽风，分类也不会跑偏——面试可以讲这个取舍。
"""
from .llm import chat_json

SEVERITY = {"bug": "high", "case_error": "low", "env": "medium"}


def rule_verdict(want_status: int, got_status: int) -> tuple[str, str]:
    want, got = int(want_status), int(got_status)
    if got == 0:
        return "env", "请求未发出（连接失败/超时），属于环境问题"
    if got >= 500 and want < 500:
        return "bug", f"接口返回 {got}，服务端未处理该输入（期望 {want}）"
    if want == 401 and got == 200:
        return "bug", "未携带凭证却返回 200，鉴权可绕过"
    if got in (401, 403) and want != got:
        return "env", f"返回 {got}：鉴权失败（Cookie/Token 缺失或已过期），先确认登录态再判断是否缺陷"
    if want < 500 and 400 <= got < 500 and got != want:
        return "case_error", f"期望 {want}，实际 {got}，二者都是客户端错误，应检查用例断言"
    return "case_error", f"期望 {want}，实际 {got}，需核对用例参数"


async def triage_failures(items: list[dict]) -> list[dict]:
    """items: [{run_item_id, case_name, method, path, want_status, got_status, resp_body}]"""
    out = []
    for it in items:
        verdict, reason = rule_verdict(it["want_status"], it["got_status"])
        out.append(
            {
                "run_item_id": it["run_item_id"],
                "verdict": verdict,
                "reason": reason,
                "severity": SEVERITY.get(verdict, "medium"),
            }
        )

    try:
        payload = [
            {
                "id": o["run_item_id"],
                "case": it["case_name"],
                "api": f'{it["method"]} {it["path"]}',
                "expect": it["want_status"],
                "actual": it["got_status"],
                "body": (it["resp_body"] or "")[:200],
            }
            for o, it in zip(out, items)
        ]
        refined = await chat_json(
            "你是测试专家。对每个失败用例写一句不超过 40 字的中文原因解释。"
            '只输出 JSON 数组：[{"id":1,"reason":"..."}]',
            str(payload),
        )
        if isinstance(refined, list):
            by_id = {
                int(x.get("id")): str(x.get("reason", ""))[:120]
                for x in refined
                if isinstance(x, dict) and x.get("id") is not None
            }
            for o in out:
                if by_id.get(o["run_item_id"]):
                    o["reason"] = by_id[o["run_item_id"]]
    except Exception:  # noqa: BLE001  模型失败不影响规则判定
        pass

    return out
