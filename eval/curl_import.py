"""验证：粘贴一条 curl 就能建接口 + 直接跑出结果（不依赖 OpenAPI）。"""
import time

import httpx

c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)
tok = c.post("/api/auth/login", json={"email": "admin@demo.com", "password": "demo1234"}).json()["token"]
h = {"Authorization": f"Bearer {tok}"}

CURL = (
    'curl -X POST http://127.0.0.1:9000/users '
    '-H "Authorization: Bearer mock-token" -H "Content-Type: application/json" '
    '-d \'{"email":"a@b.c","name":"x"}\''
)

print("=== 1. 新建空项目 ===")
r = c.post("/api/projects", json={"name": "cURL 导入验证", "base_url": "http://127.0.0.1:9999"}, headers=h)
pid = r.json()["id"]
print(f"  项目 id={pid}（故意把地址写成 9999，验证导入时会自动纠正）")

print("\n=== 2. 粘贴 curl 导入 ===")
r = c.post(f"/api/projects/{pid}/import/curl", json={"curl": CURL}, headers=h)
print(f"  HTTP {r.status_code} {r.text[:300]}")

print("\n=== 3. 看接口与用例 ===")
eps = c.get(f"/api/projects/{pid}/endpoints", headers=h).json()
cases = c.get(f"/api/projects/{pid}/cases", headers=h).json()
print(f"  接口 {len(eps)} 个：{[(e['method'], e['path']) for e in eps]}")
print(f"  用例 {len(cases)} 条：{[x['name'] for x in cases]}")

print("\n=== 4. 直接执行（不调模型）===")
r = c.post("/api/runs", json={"project_id": pid}, headers=h)
rid = r.json().get("run_id")
for _ in range(120):
    time.sleep(0.5)
    d = c.get(f"/api/runs/{rid}", headers=h).json()
    if d["status"] in ("done", "awaiting_confirm", "failed"):
        break
print(f"  状态 {d['status']} | 总数 {d['total']} 通过 {d['passed']} 失败 {d['failed']} | {d['duration_ms']}ms")
for i in d["items"]:
    print(f"    {i['status']:6} {i['method']} {i['path']} | {i['case_name']} | {i['resp_status']}")

print("\n=== 5. 项目地址是否被自动纠正 ===")
p = c.get(f"/api/projects/{pid}", headers=h).json()
print(f"  base_url = {p['base_url']}")
