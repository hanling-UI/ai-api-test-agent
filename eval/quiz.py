"""5 项测验：真实调用 API，打印每一步结果。"""
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000"
PWD = "demo1234"
c = httpx.Client(base_url=BASE, timeout=60)


def login(email):
    r = c.post("/api/auth/login", json={"email": email, "password": PWD})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


def wait_run(h, rid, timeout=120):
    for _ in range(timeout):
        time.sleep(0.5)
        d = c.get(f"/api/runs/{rid}", headers=h).json()
        if d["status"] in ("done", "awaiting_confirm", "failed"):
            return d
    return d


admin = login("admin@demo.com")
viewer = login("viewer@demo.com")

projects = c.get("/api/projects", headers=admin).json()
pid = projects[0]["id"]
print(f"项目：{projects[0]['name']}（{projects[0]['endpoint_count']} 接口 / {projects[0]['case_count']} 用例）\n")

# ---------- 任务 1：禁用一条用例，看总数变化 ----------
cases = c.get(f"/api/projects/{pid}/cases", headers=admin).json()
target = next((x for x in cases if x["enabled"]), None)
print("【任务 1】禁用一条用例，看执行总数变化")
print(f"  禁用：{target['name']}")
c.patch(f"/api/cases/{target['id']}", json={"enabled": False}, headers=admin)

run1 = c.post("/api/runs", json={"project_id": pid}, headers=admin).json()["run_id"]
d1 = wait_run(admin, run1)
print(f"  跑批 #{run1}：总数 {d1['total']}（禁用前是 46）")

# 恢复
c.patch(f"/api/cases/{target['id']}", json={"enabled": True}, headers=admin)
print(f"  已恢复该用例\n")

# ---------- 任务 2 & 3：从失败里各挑一条 ----------
items = d1["items"]
bug_item = next((i for i in items if i["verdict"] == "bug"), None)
case_item = next((i for i in items if i["verdict"] == "case_error"), None)

print("【任务 2】找一条归因为「bug」的失败")
if bug_item:
    print(f"  {bug_item['method']} {bug_item['path']} · {bug_item['case_name']}")
    print(f"  期望 {bug_item['request'].get('expected_status', '?')}，实际 {bug_item['resp_status']}")
    for chk in (bug_item.get("assert_detail") or {}).get("checks", []):
        if not chk.get("ok"):
            print(f"  断言失败：{chk['name']} 期望 {chk['expected']}，实际 {chk['actual']}")
    print(f"  归因理由：{bug_item['verdict_reason']}")
    print(f"  响应体：{(bug_item['resp_body'] or '')[:120]}")
else:
    print("  没找到（可能这批没判出 bug）")
print()

print("【任务 3】找一条归因为「case_error」的失败（不是接口的错）")
if case_item:
    print(f"  {case_item['method']} {case_item['path']} · {case_item['case_name']}")
    print(f"  实际返回 {case_item['resp_status']}")
    print(f"  归因理由：{case_item['verdict_reason']}")
    print("  为什么不算 bug：用例本身假设错了（比如期待 201，但 200 也是合理的）")
print()

# ---------- 任务 4：提交一条缺陷 ----------
print("【任务 4】提交一条缺陷，看状态 draft → submitted")
issues = c.get(f"/api/projects/{pid}/issues", headers=admin).json()
draft = next((i for i in issues if i["status"] == "draft"), None)
if draft:
    print(f"  提交前状态：{draft['status']}｜{draft['title'][:50]}")
    r = c.post("/api/issues/confirm", json={"issue_ids": [draft["id"]]}, headers=admin)
    print(f"  提交接口返回：{r.status_code} {r.json()}")
    after = c.get(f"/api/projects/{pid}/issues", headers=admin).json()
    one = next(i for i in after if i["id"] == draft["id"])
    print(f"  提交后状态：{one['status']}")
else:
    print("  没有草稿，先跑一批（前面已经跑过，应该有）")
print()

# ---------- 任务 5：只读用户不能执行 ----------
print("【任务 5】用 viewer 登录后执行，应被拒绝")
r = c.post("/api/runs", json={"project_id": pid}, headers=viewer)
print(f"  HTTP {r.status_code} · {r.text[:80]}")
print()

# ---------- 总结 ----------
stats = c.get(f"/api/projects/{pid}/stats", headers=admin).json()
print("【统计】", stats)
