"""初始化演示数据：3 个账号 + 1 个项目 + 成员关系。

用法：
    python -m app.seed            # 只建账号和项目
    python -m app.seed --demo     # 再导入 mock 服务的 OpenAPI 并生成用例
"""
import asyncio
import sys

import httpx

from .config import DEMO_PASSWORD, TARGET_BASE_URL
from .db import SessionLocal, init_db
from .models import Project, ProjectMember, User
from .security import hash_password

ACCOUNTS = [
    ("admin@demo.com", "管理员"),
    ("tester@demo.com", "测试同学"),
    ("viewer@demo.com", "只读访客"),
]


def seed() -> dict:
    init_db()
    db = SessionLocal()
    try:
        users = {}
        for email, name in ACCOUNTS:
            user = db.query(User).filter(User.email == email).first()
            if user is None:
                user = User(email=email, name=name,
                            password_hash=hash_password(DEMO_PASSWORD))
                db.add(user)
                db.flush()
            if email == "admin@demo.com":
                user.is_system_admin = True
            users[email] = user

        project = db.query(Project).filter(Project.name == "示例商城 API").first()
        if project is None:
            project = Project(name="示例商城 API", base_url=TARGET_BASE_URL,
                              env="test", owner_id=users["admin@demo.com"].id)
            db.add(project)
            db.flush()

        roles = {
            "admin@demo.com": "admin",
            "tester@demo.com": "tester",
            "viewer@demo.com": "viewer",
        }
        for email, role in roles.items():
            exists = (
                db.query(ProjectMember)
                .filter(ProjectMember.project_id == project.id,
                        ProjectMember.user_id == users[email].id)
                .first()
            )
            if exists is None:
                db.add(ProjectMember(project_id=project.id,
                                     user_id=users[email].id, role=role))
        db.commit()
        return {"project_id": project.id, "password": DEMO_PASSWORD}
    finally:
        db.close()


async def demo(project_id: int) -> None:
    """拉 mock 服务的 OpenAPI，导入接口并生成用例。"""
    from .services.generator import generate_cases, save_cases
    from .services.parser import parse_openapi
    from .models import Case, Endpoint

    async with httpx.AsyncClient(timeout=20) as client:
        spec = (await client.get(f"{TARGET_BASE_URL.rstrip('/')}/openapi.json")).json()

    endpoints = parse_openapi(spec)
    db = SessionLocal()
    try:
        db.query(Case).filter(
            Case.endpoint_id.in_(db.query(Endpoint.id).filter(Endpoint.project_id == project_id))
        ).delete(synchronize_session=False)
        db.query(Endpoint).filter(Endpoint.project_id == project_id).delete(synchronize_session=False)
        for ep in endpoints:
            db.add(Endpoint(project_id=project_id, **ep))
        db.commit()

        eps = db.query(Endpoint).filter(Endpoint.project_id == project_id).all()
        added = 0
        for ep in eps:
            cases = await generate_cases(ep)
            added += save_cases(db, ep, cases)
        from .services.golden import insert_golden_cases

        golden = insert_golden_cases(db, project_id)
        print(f"导入 {len(eps)} 个接口，生成 {added} 条用例，基线 {golden} 条")
    finally:
        db.close()


if __name__ == "__main__":
    info = seed()
    print(f"演示账号密码：{info['password']}")
    if "--demo" in sys.argv:
        asyncio.run(demo(info["project_id"]))
