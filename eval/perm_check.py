"""验证修复后的权限模型。"""
import httpx

c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30)
PWD = "demo1234"


def login(email):
    tok = c.post("/api/auth/login", json={"email": email, "password": PWD}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


admin, tester, viewer = login("admin@demo.com"), login("tester@demo.com"), login("viewer@demo.com")

print("=== 1. 各角色能看到的项目 ===")
for name, h in (("管理员", admin), ("测试", tester), ("访客", viewer)):
    ps = c.get("/api/projects", headers=h).json()
    print(f"  {name}: " + ", ".join(f"{p['name']}({p['role']})" for p in ps))

print("\n=== 2. 访客/测试尝试新建项目（应 403）===")
for name, h in (("访客", viewer), ("测试", tester)):
    r = c.post("/api/projects", json={"name": "偷偷建的项目", "base_url": "http://127.0.0.1:9000"}, headers=h)
    print(f"  {name}: HTTP {r.status_code} {r.text[:70]}")

print("\n=== 3. 管理员新建 + 删除（DELETE 路由是否生效）===")
r = c.post("/api/projects", json={"name": "临时删除测试", "base_url": "http://127.0.0.1:9000"}, headers=admin)
pid = r.json()["id"]
print(f"  新建: HTTP {r.status_code} id={pid}")
r = c.delete(f"/api/projects/{pid}", headers=admin)
print(f"  删除: HTTP {r.status_code} {r.text[:60]}（405 就说明还是旧进程）")

print("\n=== 4. 访客尝试删除管理员的项目（应 403）===")
r = c.delete("/api/projects/1", headers=viewer)
print(f"  HTTP {r.status_code} {r.text[:70]}")

print("\n=== 5. 各角色在示例项目里的权限 ===")
for name, h in (("管理员", admin), ("测试", tester), ("访客", viewer)):
    r = c.post("/api/runs", json={"project_id": 1}, headers=h)
    print(f"  {name} 执行跑批: HTTP {r.status_code} {'✅允许' if r.status_code == 200 else '⛔拒绝'}")
