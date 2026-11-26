"""在一个全新项目上跑完整流程，验证 Agent 真的能用。"""
import time

import httpx

c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=120)
tok = c.post("/api/auth/login", json={"email": "admin@demo.com", "password": "demo1234"}).json()["token"]
h = {"Authorization": f"Bearer {tok}"}


def step(title):
    print(f"\n=== {title} ===")


step("1. 新建项目")
r = c.post("/api/projects", json={"name": "验收项目A", "base_url": "http://127.0.0.1:9000", "env": "test"}, headers=h)
print(f"  HTTP {r.status_code} {r.text[:120]}")
pid = r.json().get("id")
if not pid:
    raise SystemExit("建项目失败")

step("2. 导入 OpenAPI（从被测服务拉取）")
r = c.post(f"/api/projects/{pid}/import", json={}, headers=h)
print(f"  HTTP {r.status_code} {r.text[:200]}")

step("3. 查看接口")
r = c.get(f"/api/projects/{pid}/endpoints", headers=h)
eps = r.json() if r.status_code == 200 else []
print(f"  HTTP {r.status_code} 接口数 {len(eps)}")
for e in eps[:4]:
    print(f"    {e['method']} {e['path']} | 用例 {e['case_count']}")

step("4. 生成用例（调模型）")
t0 = time.time()
r = c.post(f"/api/projects/{pid}/generate", json={"only_missing": True}, headers=h)
print(f"  HTTP {r.status_code} {r.text[:200]} 耗时 {int(time.time()-t0)}s")

step("5. 查看用例")
r = c.get(f"/api/projects/{pid}/cases", headers=h)
cases = r.json() if r.status_code == 200 else []
print(f"  HTTP {r.status_code} 用例数 {len(cases)}")
for x in cases[:5]:
    print(f"    [{x['dimension']}] {x['name']}")

step("6. 执行跑批")
if not cases:
    print("  没有用例，跳过执行")
else:
    r = c.post("/api/runs", json={"project_id": pid}, headers=h)
    print(f"  创建跑批 HTTP {r.status_code} {r.text[:100]}")
    rid = r.json().get("run_id")
    for _ in range(240):
        time.sleep(0.5)
        d = c.get(f"/api/runs/{rid}", headers=h).json()
        if d["status"] in ("done", "awaiting_confirm", "failed"):
            break
    print(f"  结果：{d['status']} | 总数 {d['total']} 通过 {d['passed']} 失败 {d['failed']} | {d['duration_ms']}ms")
    bugs = [i for i in d["items"] if i["verdict"] == "bug"]
    print(f"  判定 bug {len(bugs)} 条：")
    for b in bugs[:5]:
        print(f"    - {b['method']} {b['path']} | {b['case_name'][:30]} | 实际 {b['resp_status']}")

    step("7. 缺陷草稿")
    r = c.get(f"/api/projects/{pid}/issues", headers=h)
    print(f"  HTTP {r.status_code} 缺陷 {len(r.json())} 条")
