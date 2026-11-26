"""验证三种角色的权限差异。"""
import httpx

c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30)
PWD = "demo1234"


def h(email):
    r = c.post("/api/auth/login", json={"email": email, "password": PWD})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


admin, tester, viewer = h("admin@demo.com"), h("tester@demo.com"), h("viewer@demo.com")
pid = c.get("/api/projects", headers=admin).json()[0]["id"]

print(f"项目 {pid}\n")

print("【管理员】成员列表")
r = c.get(f"/api/projects/{pid}/members", headers=admin)
print(f"  HTTP {r.status_code} {r.json()}")

print("\n【管理员】把 tester 降级为 viewer，再改回来")
r = c.patch(f"/api/projects/{pid}/members/2", json={"email": "", "role": "viewer"}, headers=admin)
print(f"  降级: {r.status_code} {r.text[:80]}")
r = c.patch(f"/api/projects/{pid}/members/2", json={"email": "", "role": "tester"}, headers=admin)
print(f"  恢复: {r.status_code} {r.text[:80]}")

print("\n【管理员】加一个已存在账号为只读")
r = c.post(f"/api/projects/{pid}/members", json={"email": "viewer@demo.com", "role": "viewer"}, headers=admin)
print(f"  {r.status_code} {r.text[:80]}")

print("\n【管理员】审计日志（前 5 条）")
r = c.get(f"/api/projects/{pid}/audit", headers=admin)
print(f"  HTTP {r.status_code}")
for row in r.json()[:5]:
    print(f"    {row['actor']} · {row['action']} · {row['target']}")

print("\n【测试员】尝试看成员 → 应 403")
r = c.get(f"/api/projects/{pid}/members", headers=tester)
print(f"  HTTP {r.status_code} {r.text[:60]}")

print("【测试员】尝试看审计 → 应 403")
r = c.get(f"/api/projects/{pid}/audit", headers=tester)
print(f"  HTTP {r.status_code} {r.text[:60]}")

print("【测试员】生成用例 → 允许（无 key 时给友好提示）")
r = c.post(f"/api/projects/{pid}/generate", json={"only_missing": True}, headers=tester)
print(f"  HTTP {r.status_code} {r.text[:80]}")

print("\n【只读】执行跑批 → 应 403")
r = c.post("/api/runs", json={"project_id": pid}, headers=viewer)
print(f"  HTTP {r.status_code} {r.text[:60]}")

print("【只读】提交缺陷 → 应 403")
r = c.post("/api/issues/confirm", json={"issue_ids": [1]}, headers=viewer)
print(f"  HTTP {r.status_code} {r.text[:60]}")
