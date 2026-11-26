"""本地端到端验证：登录 → 跑批 → 归因 → 提单。"""
import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000"
EMAIL = "tester@demo.com"
PASSWORD = "demo1234"

ok = True


def say(name, cond, extra=""):
    global ok
    if not cond:
        ok = False
    print(f"  [{'OK  ' if cond else 'FAIL'}] {name} {extra}")


c = httpx.Client(base_url=BASE, timeout=30)

r = c.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
say("登录", r.status_code == 200, f"status={r.status_code}")
token = r.json()["token"]
h = {"Authorization": f"Bearer {token}"}

r = c.get("/api/me", headers=h)
me = r.json()
say("获取身份", r.status_code == 200, f"projects={me.get('projects')}")

r = c.get("/api/projects", headers=h)
projects = r.json()
say("项目列表", isinstance(projects, list) and len(projects) > 0)
pid = projects[0]["id"]
print(f"       项目: {projects[0]['name']} | 接口 {projects[0]['endpoint_count']} | 用例 {projects[0]['case_count']}")

r = c.get(f"/api/projects/{pid}/stats", headers=h)
print("       统计:", json.dumps(r.json(), ensure_ascii=False))

r = c.post("/api/runs", json={"project_id": pid}, headers=h)
say("创建跑批", r.status_code == 200, f"status={r.status_code} body={r.text[:120]}")
rid = r.json().get("run_id")

status = None
for _ in range(180):
    time.sleep(1)
    r = c.get(f"/api/runs/{rid}", headers=h)
    data = r.json()
    status = data.get("status")
    if status in ("done", "awaiting_confirm", "failed"):
        break
say("跑批结束", status in ("done", "awaiting_confirm"), f"status={status}")
print(f"       总数 {data.get('total')} 通过 {data.get('passed')} 失败 {data.get('failed')} 耗时 {data.get('duration_ms')}ms")

failed = [i for i in data.get("items", []) if i["status"] != "passed"]
print(f"       失败 {len(failed)} 条：")
for i in failed[:8]:
    print(f"         - {i['method']} {i['path']} | {i['case_name'][:30]} | {i['resp_status']} | verdict={i['verdict']} | {i['verdict_reason'][:40]}")

say("有失败用例", len(failed) > 0)
say("归因完成", all(i["verdict"] for i in failed))

r = c.get(f"/api/projects/{pid}/issues", headers=h)
issues = r.json()
say("缺陷草稿已生成", len(issues) > 0, f"count={len(issues)}")
for it in issues[:5]:
    print(f"         - [{it['severity']}] {it['title'][:60]}")

if issues:
    ids = [i["id"] for i in issues if i["status"] == "draft"]
    r = c.post("/api/issues/confirm", json={"issue_ids": ids}, headers=h)
    say("确认提单", r.status_code == 200, f"status={r.status_code} {r.text[:80]}")
    r = c.get(f"/api/projects/{pid}/issues", headers=h)
    say("缺陷状态变已提交", all(i["status"] == "submitted" for i in r.json()))

# 权限：viewer 不能建跑批
r = c.post("/api/auth/login", json={"email": "viewer@demo.com", "password": PASSWORD})
vh = {"Authorization": f"Bearer {r.json()['token']}"}
r = c.post("/api/runs", json={"project_id": pid}, headers=vh)
say("viewer 被拒绝（403）", r.status_code == 403, f"status={r.status_code}")

print("\n结果:", "全部通过" if ok else "有失败项")
sys.exit(0 if ok else 1)
