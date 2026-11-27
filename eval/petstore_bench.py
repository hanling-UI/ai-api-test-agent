"""在线上跑一次 Petstore 公开规范，拿真实基准数字。"""
import time

import httpx

import os
BASE = os.getenv("BENCH_BASE", "https://ai-api-test-agent.onrender.com")
SPEC = "https://petstore3.swagger.io/api/v3/openapi.json"
PET_BASE = "https://petstore3.swagger.io/api/v3"

c = httpx.Client(base_url=BASE, timeout=180)

print("登录…")
r = c.post("/api/auth/login", json={"email": "admin@demo.com", "password": "demo1234"})
r.raise_for_status()
h = {"Authorization": f"Bearer {r.json()['token']}"}
print("  ok")

print("建项目…")
r = c.post("/api/projects", json={"name": "Petstore 公开基准", "base_url": PET_BASE, "env": "test"}, headers=h)
print(" ", r.status_code, r.text[:120])
pid = r.json().get("id")
if not pid:
    raise SystemExit("建项目失败")

print("导入 Petstore 规范…")
r = c.post(f"/api/projects/{pid}/import", json={"spec_url": SPEC}, headers=h)
print(" ", r.status_code, r.text[:200])

eps = c.get(f"/api/projects/{pid}/endpoints", headers=h).json()
gets = [e for e in eps if e["method"] in ("GET", "HEAD")]
print(f"  接口 {len(eps)} 个，其中只读 {len(gets)} 个")

print("生成用例（仅只读，需 1~3 分钟）…")
t0 = time.time()
r = c.post(f"/api/projects/{pid}/generate", json={"only_missing": True, "read_only": True}, headers=h)
print(" ", r.status_code, r.text[:200], f"耗时 {int(time.time()-t0)}s")

cases = c.get(f"/api/projects/{pid}/cases", headers=h).json()
print(f"  用例 {len(cases)} 条")

if not cases:
    raise SystemExit("没有生成用例，终止")

print("执行…")
rid = c.post("/api/runs", json={"project_id": pid}, headers=h).json()["run_id"]
for _ in range(600):
    time.sleep(2)
    d = c.get(f"/api/runs/{rid}", headers=h).json()
    if d["status"] in ("done", "awaiting_confirm", "failed"):
        break

items = d["items"]
bugs = [i for i in items if i["verdict"] == "bug"]
case_err = [i for i in items if i["verdict"] == "case_error"]
env = [i for i in items if i["verdict"] == "env"]
print("\n=== 结果 ===")
print(f"  总数 {d['total']} | 通过 {d['passed']} | 失败 {d['failed']} | 通过率 {round(d['passed']/max(d['total'],1)*100)}% | {d['duration_ms']}ms")
print(f"  归因：bug {len(bugs)} / case_error {len(case_err)} / env {len(env)}")
for b in bugs[:5]:
    print(f"    bug: {b['method']} {b['path']} | {b['case_name'][:30]} | {b['resp_status']}")

stats = c.get(f"/api/projects/{pid}/stats", headers=h).json()
print("  统计:", stats)
print("PID=", pid, "RID=", rid)
