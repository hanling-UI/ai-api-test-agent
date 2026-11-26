"""基线用例（人工维护）。

为什么需要它们：
模型生成的用例覆盖面广，但不保证命中那几个**已知的、必须被发现的**缺陷。
基线用例是"回归底线"——每次跑批都必须过，不过就是真 bug。

面试可以讲：LLM 生成 + 人工基线，两者互补，避免"全靠模型"的不确定性。
"""

GOLDEN_CASES = [
    {
        "method": "POST",
        "path": "/users",
        "name": "[基线] 缺少 name 应返回 400",
        "dimension": "error",
        "request": {"params": {}, "json": {"email": "tester@demo.com"}, "headers": {},
                    "auth_bypass": False},
        "expect": {"status": 400, "json_has": {}, "max_ms": 3000},
    },
    {
        "method": "GET",
        "path": "/orders/{order_id}",
        "name": "[基线] 未带凭证读取订单应返回 401",
        "dimension": "auth",
        "request": {"params": {"order_id": 1}, "json": {}, "headers": {},
                    "auth_bypass": True},
        "expect": {"status": 401, "json_has": {}, "max_ms": 3000},
    },
    {
        "method": "GET",
        "path": "/users",
        "name": "[基线] page=-1 应返回 400",
        "dimension": "boundary",
        "request": {"params": {"page": -1}, "json": {}, "headers": {},
                    "auth_bypass": False},
        "expect": {"status": 400, "json_has": {}, "max_ms": 3000},
    },
    {
        "method": "GET",
        "path": "/health",
        "name": "[基线] 健康检查应返回 200",
        "dimension": "normal",
        "request": {"params": {}, "json": {}, "headers": {}, "auth_bypass": False},
        "expect": {"status": 200, "json_has": {"status": "ok"}, "max_ms": 3000},
    },
]
