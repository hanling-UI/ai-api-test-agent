"""首次启动自动初始化：账号 + 示例项目 + 接口 + 基线用例。

不调模型（省钱、秒级完成），生成更用例留给用户在界面点。
幂等：已经有数据就跳过。
"""
import logging
import os

import httpx

from .db import SessionLocal
from .fixtures import GOLDEN_CASES
from .models import Case, Endpoint, Project, ProjectMember, User
from .security import hash_password
from .services.generator import fingerprint
from .services.parser import parse_openapi

logger = logging.getLogger(__name__)

ACCOUNTS = [
    ("admin@demo.com", "管理员", True),
    ("tester@demo.com", "测试同学", False),
    ("viewer@demo.com", "只读访客", False),
]
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo1234")
TARGET_BASE_URL = os.getenv("TARGET_BASE_URL", "http://127.0.0.1:9000")


def _ensure_users(db) -> dict:
    users = {}
    for email, name, is_admin in ACCOUNTS:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(email=email, name=name, password_hash=hash_password(DEMO_PASSWORD))
            db.add(user)
            db.flush()
        if is_admin:
            user.is_system_admin = True
        users[email] = user
    db.commit()
    return users


def _ensure_project(db, admin: User) -> Project:
    project = db.query(Project).filter(Project.name == "示例商城 API").first()
    if project is None:
        project = Project(name="示例商城 API", base_url=TARGET_BASE_URL,
                          env="test", owner_id=admin.id)
        db.add(project)
        db.flush()
    roles = {"admin@demo.com": "admin", "tester@demo.com": "tester", "viewer@demo.com": "viewer"}
    for email, role in roles.items():
        user = db.query(User).filter(User.email == email).first()
        if not user:
            continue
        exists = (db.query(ProjectMember)
                  .filter(ProjectMember.project_id == project.id,
                          ProjectMember.user_id == user.id).first())
        if not exists:
            db.add(ProjectMember(project_id=project.id, user_id=user.id, role=role))
    db.commit()
    return project


def _ensure_endpoints(db, project: Project) -> int:
    if db.query(Endpoint).filter(Endpoint.project_id == project.id).count() > 0:
        return 0
    try:
        with httpx.Client(timeout=6) as client:
            spec = client.get(f"{TARGET_BASE_URL.rstrip('/')}/openapi.json").json()
    except Exception as exc:  # noqa: BLE001  被测服务还没起来就跳过
        logger.warning("初始化：拉取 OpenAPI 失败（%s），跳过接口导入", exc)
        return 0

    endpoints = parse_openapi(spec)
    for ep in endpoints:
        db.add(Endpoint(project_id=project.id, **ep))
    db.commit()
    return len(endpoints)


def _ensure_golden_cases(db, project: Project) -> int:
    endpoints = db.query(Endpoint).filter(Endpoint.project_id == project.id).all()
    by_key = {(e.method.upper(), e.path): e for e in endpoints}
    added = 0
    for item in GOLDEN_CASES:
        ep = by_key.get((item["method"].upper(), item["path"]))
        if ep is None:
            continue
        request = {**item["request"], "method": ep.method, "path": ep.path}
        fp = fingerprint(ep, item["dimension"], request)
        if db.query(Case).filter(Case.fingerprint == fp).first():
            continue
        db.add(Case(endpoint_id=ep.id, name=item["name"], dimension=item["dimension"],
                    request=request, expect=item["expect"], source="manual", fingerprint=fp))
        added += 1
    db.commit()
    return added


def bootstrap() -> None:
    db = SessionLocal()
    try:
        users = _ensure_users(db)
        project = _ensure_project(db, users["admin@demo.com"])
        n_ep = _ensure_endpoints(db, project)
        n_case = _ensure_golden_cases(db, project)
        logger.info("初始化完成：项目=%s，新增接口 %s，新增基线用例 %s",
                    project.name, n_ep, n_case)
    except Exception as exc:  # noqa: BLE001
        logger.warning("初始化跳过（%s）", exc)
    finally:
        db.close()
