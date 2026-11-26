"""HTTP 接口层。"""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .config import OPENAI_API_KEY
from .db import SessionLocal, get_db
from .graph import resume_run, start_run
from .models import (
    AuditLog, Case, Endpoint, Issue, Project, ProjectMember, Run, RunItem, User,
)
from .security import (
    create_token, current_user, project_role, require_role, verify_password,
)
from .services.curlparse import parse_curl, parse_postman
from .services.generator import fingerprint, generate_cases, save_cases
from .services.parser import parse_openapi

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ 基础
def audit(db: Session, actor: int, action: str, target: str = "", detail: str = "") -> None:
    db.add(AuditLog(actor_id=actor, action=action, target=target[:180], detail=detail[:500]))


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "邮箱或密码错误")
    audit(db, user.id, "login", user.email)
    db.commit()
    return {
        "token": create_token(user),
        "user": {"id": user.id, "email": user.email, "name": user.name},
    }


class ProfileIn(BaseModel):
    name: str | None = None
    avatar: str | None = None


@router.patch("/me")
def update_me(payload: ProfileIn, user: User = Depends(current_user),
              db: Session = Depends(get_db)):
    """改昵称 / 头像。头像支持 emoji 或图片 URL。"""
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(400, "昵称不能为空")
        user.name = name[:60]
    if payload.avatar is not None:
        user.avatar = payload.avatar.strip()[:280]
    audit(db, user.id, "user.profile", user.email)
    db.commit()
    return {"id": user.id, "name": user.name, "avatar": user.avatar}


class PasswordIn(BaseModel):
    old_password: str
    new_password: str


@router.post("/me/password")
def change_password(payload: PasswordIn, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    from .security import hash_password, verify_password

    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(400, "原密码不正确")
    if len(payload.new_password) < 6:
        raise HTTPException(400, "新密码至少 6 位")
    user.password_hash = hash_password(payload.new_password)
    audit(db, user.id, "user.password", user.email)
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    members = db.query(ProjectMember).filter(ProjectMember.user_id == user.id).all()
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar": getattr(user, "avatar", "") or "",
        "is_admin": bool(getattr(user, "is_system_admin", False)),
        "projects": [{"project_id": m.project_id, "role": m.role} for m in members],
    }


# ------------------------------------------------------------------ 项目
@router.get("/projects")
def list_projects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if getattr(user, "is_system_admin", False):
        # 系统管理员看全部项目，角色一律按 admin 展示
        rows = [(p, type("M", (), {"role": "admin"})()) for p in db.query(Project).all()]
    else:
        rows = (
            db.query(Project, ProjectMember)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .filter(ProjectMember.user_id == user.id)
            .all()
        )
    out = []
    for project, member in rows:
        ep_count = db.query(Endpoint).filter(Endpoint.project_id == project.id).count()
        case_count = (
            db.query(Case).join(Endpoint, Endpoint.id == Case.endpoint_id)
            .filter(Endpoint.project_id == project.id).count()
        )
        last_run = (
            db.query(Run).filter(Run.project_id == project.id)
            .order_by(Run.id.desc()).first()
        )
        out.append({
            "id": project.id,
            "name": project.name,
            "base_url": project.base_url,
            "env": project.env,
            "role": member.role,
            "endpoint_count": ep_count,
            "case_count": case_count,
            "last_run": {
                "id": last_run.id,
                "status": last_run.status,
                "total": last_run.total,
                "passed": last_run.passed,
                "failed": last_run.failed,
            } if last_run else None,
        })
    return out


class ProjectIn(BaseModel):
    name: str
    base_url: str = "http://127.0.0.1:9000"
    env: str = "test"


class ProbeIn(BaseModel):
    base_url: str


@router.post("/probe")
async def probe_docs(payload: ProbeIn, user: User = Depends(current_user)):
    """探测某个地址上有没有 OpenAPI 文档，返回找到的地址与接口数。

    新建项目时用，避免用户"不知道该填什么地址"。
    """
    base = payload.base_url.rstrip("/")
    tried = []
    async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
        for path in ("/openapi.json", "/v3/api-docs", "/swagger.json",
                     "/apispec_1.json", "/api-docs", "/docs/openapi.json"):
            url = base + path
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict) and data.get("paths"):
                        return {"found": url, "paths_count": len(data["paths"])}
                    tried.append(f"{path} 返回的不是 OpenAPI")
                else:
                    tried.append(f"{path} → {resp.status_code}")
            except Exception as exc:  # noqa: BLE001
                tried.append(f"{path} 失败：{type(exc).__name__}")
    return {"found": None, "tried": tried}


@router.post("/projects")
def create_project(payload: ProjectIn, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    if not getattr(user, "is_system_admin", False):
        raise HTTPException(403, "只有系统管理员能创建项目；请让管理员把你加进项目后再做测试")
    project = Project(name=payload.name[:110], base_url=payload.base_url,
                      env=payload.env if payload.env in ("test", "prod") else "test",
                      owner_id=user.id)
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role="admin"))
    audit(db, user.id, "project.create", payload.name)
    db.commit()
    return {"id": project.id}


class ProjectPatch(BaseModel):
    name: str | None = None
    base_url: str | None = None
    env: str | None = None
    custom_headers: dict | None = None
    auth_token: str | None = None


@router.patch("/projects/{pid}")
def patch_project(pid: int, payload: ProjectPatch, user: User = Depends(current_user),
                  db: Session = Depends(get_db)):
    """改项目地址/名称/环境。只有 admin 能改（改错地址会导致打到错误的服务）。"""
    require_role(db, user, pid, "admin")
    project = db.get(Project, pid)
    if project is None:
        raise HTTPException(404, "项目不存在")
    if payload.name:
        project.name = payload.name[:110]
    if payload.base_url:
        project.base_url = payload.base_url.rstrip("/")
    if payload.env in ("test", "prod"):
        project.env = payload.env
    if payload.custom_headers is not None:
        project.custom_headers = payload.custom_headers
    if payload.auth_token is not None:
        project.auth_token = payload.auth_token
    audit(db, user.id, "project.update", f"project={pid}", f"base_url={project.base_url}")
    db.commit()
    return {"id": project.id, "name": project.name, "base_url": project.base_url, "env": project.env}


@router.delete("/projects/{pid}")
def delete_project(pid: int, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    """删除项目及其全部数据（仅 admin）。危险操作，前端有二次确认。"""
    require_role(db, user, pid, "admin")
    project = db.get(Project, pid)
    if project is None:
        raise HTTPException(404, "项目不存在")

    from sqlalchemy import text

    for sql in (
        "DELETE FROM issues WHERE project_id=:p",
        "DELETE FROM run_items WHERE run_id IN (SELECT id FROM runs WHERE project_id=:p)",
        "DELETE FROM runs WHERE project_id=:p",
        "DELETE FROM cases WHERE endpoint_id IN (SELECT id FROM endpoints WHERE project_id=:p)",
        "DELETE FROM endpoints WHERE project_id=:p",
        "DELETE FROM project_members WHERE project_id=:p",
        "DELETE FROM projects WHERE id=:p",
    ):
        db.execute(text(sql), {"p": pid})
    audit(db, user.id, "project.delete", project.name)
    db.commit()
    return {"ok": True, "deleted": pid}


@router.get("/projects/{pid}")
def get_project(pid: int, user: User = Depends(current_user),
                db: Session = Depends(get_db)):
    project = db.get(Project, pid)
    if project is None:
        raise HTTPException(404, "项目不存在")
    role = require_role(db, user, pid, "viewer")
    return {
        "id": project.id, "name": project.name, "base_url": project.base_url,
        "env": project.env, "role": role,
    }


# ------------------------------------------------------------------ 接口与用例
class ImportIn(BaseModel):
    spec_url: str | None = None
    spec: dict | None = None
    spec_text: str | None = None      # 上传的文件内容（JSON 或 YAML）
    exclude_infra: bool = True        # 排除登录/登出/静态/文档等非业务接口


# 不属于业务 API 的路径前缀：门禁、静态资源、接口文档本身
INFRA_PREFIXES = (
    "/login", "/logout", "/signin", "/signout", "/auth/",
    "/static/", "/site/", "/assets/", "/favicon",
    "/docs", "/redoc", "/openapi.json", "/swagger",
    "/.well-known/",
)


def _is_infra(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in INFRA_PREFIXES)


@router.post("/projects/{pid}/import")
async def import_spec(pid: int, payload: ImportIn, user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    require_role(db, user, pid, "tester")
    project = db.get(Project, pid)

    spec = payload.spec
    if spec is None and payload.spec_text:
        text = payload.spec_text
        try:
            spec = json.loads(text)
        except Exception:  # noqa: BLE001
            try:
                import yaml

                spec = yaml.safe_load(text)
            except Exception:  # noqa: BLE001
                raise HTTPException(400, "文件解析失败：只支持 OpenAPI 的 JSON 或 YAML")
    if spec is None:
        base = project.base_url.rstrip("/")
        # 不同框架的文档路径不一样，按常见顺序探测
        candidates = (
            [payload.spec_url] if payload.spec_url
            else [f"{base}/openapi.json", f"{base}/v3/api-docs", f"{base}/swagger.json",
                  f"{base}/apispec_1.json", f"{base}/api-docs", f"{base}/docs/openapi.json"]
        )
        # 带上项目配置的请求头（Cookie / API-Key），否则拿不到需要登录的文档
        fetch_headers = dict(project.custom_headers or {})
        if project.auth_token and not any(k.lower() == "authorization" for k in fetch_headers):
            fetch_headers["Authorization"] = f"Bearer {project.auth_token}"

        last_err = None
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                for cand in candidates:
                    try:
                        resp = await client.get(cand, headers=fetch_headers)
                        if resp.status_code != 200:
                            last_err = f"{cand} 返回 {resp.status_code}"
                            continue
                        data = resp.json()
                        if isinstance(data, dict) and data.get("paths"):
                            spec, url = data, cand
                            break
                        last_err = f"{cand} 不是有效的 OpenAPI（没有 paths）"
                    except Exception as exc:  # noqa: BLE001
                        last_err = f"{cand} 失败：{exc}"
        except httpx.ConnectError:
            raise HTTPException(
                400,
                f"连不上被测服务 {base}。请先启动它（演示环境：运行 run_mock.py，端口 9000），"
                "或点「修改地址」换成正确的服务地址。",
            )
        except httpx.TimeoutException:
            raise HTTPException(400, f"拉取 {base} 超时，检查被测服务是否卡住")

        if spec is None:
            raise HTTPException(
                400,
                f"在 {base} 上没找到 OpenAPI 文档。已尝试：openapi.json / v3/api-docs / "
                f"swagger.json / apispec_1.json / api-docs / docs/openapi.json。"
                f"最后错误：{last_err}。也可以点「上传 spec 文件」直接传文档。",
            )

    endpoints = parse_openapi(spec)
    total_before = len(endpoints)
    if payload.exclude_infra:
        endpoints = [ep for ep in endpoints if not _is_infra(ep["path"])]
    if not endpoints:
        raise HTTPException(400, "没有解析到任何接口（可能全被当作认证/文档类排除了）")

    # 按依赖顺序清理：审计/缺陷 → 结果 → 跑批 → 用例 → 接口
    # 直接删 cases 会撞上 run_items 的外键，所以先清结果
    from sqlalchemy import text

    db.execute(text("DELETE FROM issues WHERE project_id = :pid"), {"pid": pid})
    db.execute(
        text("DELETE FROM run_items WHERE run_id IN (SELECT id FROM runs WHERE project_id = :pid)"),
        {"pid": pid},
    )
    db.execute(text("DELETE FROM runs WHERE project_id = :pid"), {"pid": pid})
    db.execute(
        text("DELETE FROM cases WHERE endpoint_id IN (SELECT id FROM endpoints WHERE project_id = :pid)"),
        {"pid": pid},
    )
    db.execute(text("DELETE FROM endpoints WHERE project_id = :pid"), {"pid": pid})
    db.commit()

    for ep in endpoints:
        db.add(Endpoint(project_id=pid, **ep))
    audit(db, user.id, "spec.import", f"project={pid}",
          f"{len(endpoints)} endpoints, excluded={total_before - len(endpoints)}")
    db.commit()
    return {"endpoints": len(endpoints),
            "excluded": total_before - len(endpoints)}


def _upsert_endpoint(db, project_id: int, data: dict) -> tuple:
    """按 method+path 复用已有接口，返回 (endpoint, 是否新建)。"""
    ep = (
        db.query(Endpoint)
        .filter(Endpoint.project_id == project_id,
                Endpoint.method == data["method"],
                Endpoint.path == data["path"])
        .first()
    )
    fields = dict(
        summary=data.get("summary", "")[:280],
        params=data.get("params") or [],
        body_schema=data.get("body_schema") or {},
        response_schema=data.get("response_schema") or {},
        auth_type=data.get("auth_type") or "none",
    )
    if ep:
        for k, v in fields.items():
            setattr(ep, k, v)
        return ep, False
    ep = Endpoint(project_id=project_id, method=data["method"], path=data["path"], **fields)
    db.add(ep)
    db.flush()
    return ep, True


def _seed_cases_from_sample(db, ep: Endpoint, sample_params: dict, sample_body, headers: dict) -> int:
    """从 curl 的示例参数直接生成可跑的基线用例（不依赖模型）。"""
    added = 0
    base_req = {
        "method": ep.method,
        "path": ep.path,
        "params": sample_params or {},
        "json": sample_body or {},
        "headers": headers or {},
        "auth_bypass": False,
    }
    candidates = [
        ("[手工] 按示例参数请求应成功", "normal",
         base_req, {"status": 200, "json_has": {}, "max_ms": 5000}),
    ]
    if ep.auth_type != "none":
        bypass = dict(base_req)
        bypass["auth_bypass"] = True
        bypass["headers"] = {}
        candidates.append((
            "[手工] 不带凭证应返回 401", "auth", bypass,
            {"status": 401, "json_has": {}, "max_ms": 5000},
        ))

    for name, dimension, request, expect in candidates:
        fp = fingerprint(ep, dimension, request)
        if db.query(Case).filter(Case.fingerprint == fp).first():
            continue
        db.add(Case(endpoint_id=ep.id, name=name, dimension=dimension,
                    request=request, expect=expect, source="manual", fingerprint=fp))
        added += 1
    return added


class CurlIn(BaseModel):
    curl: str


class LoginIn(BaseModel):
    login_url: str | None = None      # 不填就用 base_url + /login
    password_field: str = "password"
    password: str


@router.post("/projects/{pid}/login")
async def project_login(pid: int, payload: LoginIn, user: User = Depends(current_user),
                        db: Session = Depends(get_db)):
    """用口令登录被测服务，自动把拿到的 Cookie 存成项目请求头。

    这样测试需要登录态的接口时，不用手工去浏览器复制 Cookie。
    """
    require_role(db, user, pid, "tester")
    project = db.get(Project, pid)
    url = payload.login_url or f"{project.base_url.rstrip('/')}/login"

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            resp = await client.post(url, data={payload.password_field: payload.password})
    except httpx.ConnectError:
        raise HTTPException(400, f"连不上 {url}，确认被测服务已启动")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"登录请求失败：{exc}")

    cookies = dict(resp.cookies)
    if not cookies:
        hint = "口令不对" if resp.status_code == 401 else f"返回 {resp.status_code}，没有 Set-Cookie"
        raise HTTPException(
            400,
            f"登录没拿到 Cookie（{hint}）。检查地址 {url}、字段名 {payload.password_field}、口令是否正确。",
        )

    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
    project.custom_headers = {**(project.custom_headers or {}), "Cookie": cookie_str}
    audit(db, user.id, "project.login", f"project={pid}", "获取 Cookie 成功")
    db.commit()
    keys = ", ".join(cookies.keys())
    return {"ok": True, "status": resp.status_code, "cookie_names": keys}


@router.post("/projects/{pid}/import/curl")
def import_curl(pid: int, payload: CurlIn, user: User = Depends(current_user),
                db: Session = Depends(get_db)):
    """粘贴一条 curl → 生成接口 + 可直接执行的用例（不需要 OpenAPI）。"""
    role = require_role(db, user, pid, "tester")
    if role not in ("admin", "tester"):
        raise HTTPException(403, "需要 tester 权限")
    project = db.get(Project, pid)
    try:
        data = parse_curl(payload.curl)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    # curl 指向别的服务时，顺手把项目地址改成它，避免请求打错地方
    if data.get("origin") and data["origin"] != project.base_url.rstrip("/"):
        project.base_url = data["origin"]

    ep, created = _upsert_endpoint(db, pid, data)
    cases = _seed_cases_from_sample(
        db, ep, data.get("sample_params") or {}, data.get("sample_body"), data.get("headers") or {}
    )
    audit(db, user.id, "endpoint.curl", f"project={pid}", f"{data['method']} {data['path']}")
    db.commit()
    return {
        "endpoint": {"id": ep.id, "method": ep.method, "path": ep.path},
        "created": created,
        "cases": cases,
        "base_url": project.base_url,
    }


@router.post("/projects/{pid}/import/postman")
def import_postman(pid: int, payload: ImportIn, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    """上传 Postman Collection（v2.x）→ 批量导入接口。"""
    require_role(db, user, pid, "tester")
    if not payload.spec_text:
        raise HTTPException(400, "请上传 Postman 集合 JSON")
    try:
        collection = json.loads(payload.spec_text)
    except json.JSONDecodeError:
        raise HTTPException(400, "不是合法的 JSON")

    items = parse_postman(collection)
    if not items:
        raise HTTPException(400, "这个集合里没有可用请求")

    created = 0
    for data in items:
        _, is_new = _upsert_endpoint(db, pid, data)
        created += 1 if is_new else 0
    audit(db, user.id, "endpoint.postman", f"project={pid}", f"{len(items)} requests")
    db.commit()
    return {"endpoints": len(items), "created": created}


@router.get("/projects/{pid}/endpoints")
def list_endpoints(pid: int, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    require_role(db, user, pid, "viewer")
    eps = db.query(Endpoint).filter(Endpoint.project_id == pid).order_by(Endpoint.id).all()
    out = []
    for ep in eps:
        case_count = db.query(Case).filter(Case.endpoint_id == ep.id).count()
        out.append({
            "id": ep.id, "method": ep.method, "path": ep.path, "summary": ep.summary,
            "auth_type": ep.auth_type, "case_count": case_count,
            "body_fields": list((ep.body_schema or {}).keys()),
        })
    return out


@router.get("/projects/{pid}/cases")
def list_cases(pid: int, endpoint_id: int | None = None,
               user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(db, user, pid, "viewer")
    q = db.query(Case).join(Endpoint, Endpoint.id == Case.endpoint_id).filter(
        Endpoint.project_id == pid
    )
    if endpoint_id:
        q = q.filter(Case.endpoint_id == endpoint_id)
    rows = q.order_by(Case.endpoint_id, Case.id).all()
    return [
        {
            "id": c.id, "endpoint_id": c.endpoint_id, "name": c.name,
            "dimension": c.dimension, "enabled": c.enabled,
            "request": c.request, "expect": c.expect, "source": c.source,
        }
        for c in rows
    ]


class CasePatch(BaseModel):
    enabled: bool | None = None
    name: str | None = None


@router.patch("/cases/{cid}")
def patch_case(cid: int, payload: CasePatch, user: User = Depends(current_user),
               db: Session = Depends(get_db)):
    case = db.get(Case, cid)
    if case is None:
        raise HTTPException(404, "用例不存在")
    ep = db.get(Endpoint, case.endpoint_id)
    require_role(db, user, ep.project_id, "tester")
    if payload.enabled is not None:
        case.enabled = payload.enabled
    if payload.name:
        case.name = payload.name[:180]
    audit(db, user.id, "case.update", str(cid))
    db.commit()
    return {"ok": True}


class GenerateIn(BaseModel):
    endpoint_ids: list[int] | None = None
    only_missing: bool = True


@router.post("/projects/{pid}/generate")
async def generate(pid: int, payload: GenerateIn, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    require_role(db, user, pid, "tester")
    if not OPENAI_API_KEY:
        raise HTTPException(400, "未配置 OPENAI_API_KEY，无法生成用例（执行/归因不受影响）")
    q = db.query(Endpoint).filter(Endpoint.project_id == pid)
    if payload.endpoint_ids:
        q = q.filter(Endpoint.id.in_(payload.endpoint_ids))
    endpoints = q.all()

    total_added = 0
    skipped = 0
    failed = 0
    for ep in endpoints:
        if payload.only_missing:
            if db.query(Case).filter(Case.endpoint_id == ep.id).count() > 0:
                skipped += 1
                continue
        try:
            cases = await generate_cases(ep)
            total_added += save_cases(db, ep, cases)
        except Exception as exc:  # noqa: BLE001  单个接口失败不影响整体
            failed += 1
            logger.warning("generate failed for endpoint %s: %s", ep.id, exc)

    audit(db, user.id, "cases.generate", f"project={pid}", f"added={total_added} failed={failed}")
    db.commit()
    return {"added": total_added, "skipped": skipped, "failed": failed,
            "endpoints": len(endpoints)}


# ------------------------------------------------------------------ 跑批
class RunIn(BaseModel):
    project_id: int
    token: str = ""


async def _run_job(run_id: int, actor_id: int) -> None:
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        run.status = "running"
        db.commit()
    finally:
        db.close()

    try:
        await start_run(run_id, actor_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("graph run failed, fallback to pipeline: %s", exc)
        from .services.pipeline import execute_and_analyze

        try:
            await execute_and_analyze(run_id, actor_id)
        except Exception as exc2:  # noqa: BLE001
            logger.exception("pipeline failed: %s", exc2)
            db = SessionLocal()
            try:
                run = db.get(Run, run_id)
                run.status = "failed"
                run.finished_at = datetime.now(timezone.utc)
                db.commit()
            finally:
                db.close()


@router.post("/runs")
async def create_run(payload: RunIn, user: User = Depends(current_user),
                     db: Session = Depends(get_db)):
    require_role(db, user, payload.project_id, "tester")
    project = db.get(Project, payload.project_id)
    if project.env == "prod":
        raise HTTPException(403, "演示环境不允许对 prod 项目执行写操作")

    run = Run(project_id=payload.project_id, status="pending", created_by=user.id)
    db.add(run)
    db.flush()
    audit(db, user.id, "run.create", f"run={run.id}")
    db.commit()

    asyncio.create_task(_run_job(run.id, user.id))
    return {"run_id": run.id}


@router.get("/runs/{rid}")
def get_run(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    run = db.get(Run, rid)
    if run is None:
        raise HTTPException(404, "运行不存在")
    require_role(db, user, run.project_id, "viewer")
    items = (
        db.query(RunItem, Case, Endpoint)
        .join(Case, Case.id == RunItem.case_id)
        .join(Endpoint, Endpoint.id == Case.endpoint_id)
        .filter(RunItem.run_id == rid)
        .order_by(RunItem.status.desc(), RunItem.id)
        .all()
    )
    return {
        "id": run.id, "status": run.status, "total": run.total,
        "passed": run.passed, "failed": run.failed, "duration_ms": run.duration_ms,
        "items": [
            {
                "id": item.id, "status": item.status, "case_name": case.name,
                "dimension": case.dimension, "method": ep.method, "path": ep.path,
                "resp_status": item.resp_status, "elapsed_ms": item.elapsed_ms,
                "verdict": item.verdict, "verdict_reason": item.verdict_reason,
                "request": item.request, "resp_body": (item.resp_body or "")[:800],
                "assert_detail": item.assert_detail,
            }
            for item, case, ep in items
        ],
    }


@router.get("/projects/{pid}/runs")
def list_runs(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(db, user, pid, "viewer")
    rows = (
        db.query(Run).filter(Run.project_id == pid).order_by(Run.id.desc()).limit(10).all()
    )
    return [
        {"id": r.id, "status": r.status, "total": r.total, "passed": r.passed,
         "failed": r.failed, "duration_ms": r.duration_ms,
         "started_at": r.started_at.isoformat() if r.started_at else None}
        for r in rows
    ]


@router.get("/runs/{rid}/stream")
async def stream_run(rid: int, user: User = Depends(current_user),
                     db: Session = Depends(get_db)):
    run = db.get(Run, rid)
    if run is None:
        raise HTTPException(404, "运行不存在")
    require_role(db, user, run.project_id, "viewer")

    async def gen():
        last = None
        for _ in range(300):
            s = SessionLocal()
            try:
                r = s.get(Run, rid)
                payload = {
                    "status": r.status, "total": r.total,
                    "passed": r.passed, "failed": r.failed,
                }
            finally:
                s.close()
            if payload != last:
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                last = payload
            if payload["status"] in ("done", "awaiting_confirm", "failed"):
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(gen(), media_type="text/event-stream")


# ------------------------------------------------------------------ 缺陷
@router.get("/projects/{pid}/issues")
def list_issues(pid: int, user: User = Depends(current_user),
                db: Session = Depends(get_db)):
    require_role(db, user, pid, "viewer")
    rows = (
        db.query(Issue, Endpoint)
        .join(Endpoint, Endpoint.id == Issue.endpoint_id)
        .filter(Issue.project_id == pid)
        .order_by(Issue.id.desc())
        .all()
    )
    return [
        {
            "id": i.id, "title": i.title, "severity": i.severity, "status": i.status,
            "expected": i.expected, "actual": i.actual, "steps": i.steps, "curl": i.curl,
            "method": ep.method, "path": ep.path,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i, ep in rows
    ]


class ConfirmIn(BaseModel):
    issue_ids: list[int]


@router.post("/issues/confirm")
async def confirm_issues(payload: ConfirmIn, user: User = Depends(current_user),
                         db: Session = Depends(get_db)):
    if not payload.issue_ids:
        raise HTTPException(400, "请选择要提交的缺陷")
    issues = db.query(Issue).filter(Issue.id.in_(payload.issue_ids)).all()
    if not issues:
        raise HTTPException(404, "缺陷不存在")
    require_role(db, user, issues[0].project_id, "tester")

    run_ids = set()
    for issue in issues:
        if issue.status == "draft":
            issue.status = "submitted"
            run_ids.add(issue.run_id)
    audit(db, user.id, "issue.submit", ",".join(str(i.id) for i in issues))
    db.commit()

    for rid in run_ids:
        try:
            await resume_run(rid)
        except Exception as exc:  # noqa: BLE001  图恢复失败不影响提单
            logger.warning("resume graph failed: %s", exc)
            run = db.get(Run, rid)
            if run:
                run.status = "done"
                db.commit()

    return {"submitted": len(issues)}


@router.get("/projects/{pid}/stats")
def stats(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(db, user, pid, "viewer")
    ep_total = db.query(Endpoint).filter(Endpoint.project_id == pid).count()
    ep_with_cases = (
        db.query(Endpoint.id)
        .join(Case, Case.endpoint_id == Endpoint.id)
        .filter(Endpoint.project_id == pid)
        .distinct()
        .count()
    )
    runs = db.query(Run).filter(Run.project_id == pid).order_by(Run.id.desc()).all()
    latest = runs[0] if runs else None

    # 检出/误报只看最近一次跑批——累计会把历史测试数据也算进去，数字没有意义
    if latest is not None:
        items = db.query(RunItem).filter(RunItem.run_id == latest.id).all()
        total = latest.total
        passed = latest.passed
        bugs = sum(1 for i in items if i.verdict == "bug")
        case_errors = sum(1 for i in items if i.verdict == "case_error")
        env_errors = sum(1 for i in items if i.verdict == "env")
        avg_ms = latest.duration_ms
    else:
        total = passed = bugs = case_errors = env_errors = avg_ms = 0

    return {
        "endpoints": ep_total,
        "coverage": round(ep_with_cases / ep_total * 100, 1) if ep_total else 0,
        "runs": len(runs),
        "latest_run": latest.id if latest else None,
        "cases_executed": total,
        "pass_rate": round(passed / total * 100, 1) if total else 0,
        "bugs": bugs,
        "false_positive": case_errors,
        "env_errors": env_errors,
        "avg_duration_ms": avg_ms,
    }


# ------------------------------------------------------------------ 成员管理（仅 admin）
class MemberIn(BaseModel):
    email: str
    role: str = "tester"


@router.get("/projects/{pid}/members")
def list_members(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(db, user, pid, "admin")
    rows = (
        db.query(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .filter(ProjectMember.project_id == pid)
        .all()
    )
    return [
        {"user_id": u.id, "name": u.name, "email": u.email, "role": m.role}
        for m, u in rows
    ]


@router.post("/projects/{pid}/members")
def add_member(pid: int, payload: MemberIn, user: User = Depends(current_user),
               db: Session = Depends(get_db)):
    require_role(db, user, pid, "admin")
    role = payload.role if payload.role in ("admin", "tester", "viewer") else "viewer"
    target = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if target is None:
        raise HTTPException(404, "该邮箱还没有账号，请先在系统里注册（演示环境用种子账号）")
    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == pid, ProjectMember.user_id == target.id)
        .first()
    )
    if member:
        member.role = role
    else:
        db.add(ProjectMember(project_id=pid, user_id=target.id, role=role))
    audit(db, user.id, "member.upsert", f"project={pid}", f"{target.email} -> {role}")
    db.commit()
    return {"ok": True}


@router.patch("/projects/{pid}/members/{uid}")
def change_member_role(pid: int, uid: int, payload: MemberIn,
                       user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(db, user, pid, "admin")
    role = payload.role if payload.role in ("admin", "tester", "viewer") else "viewer"
    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == pid, ProjectMember.user_id == uid)
        .first()
    )
    if member is None:
        raise HTTPException(404, "成员不存在")

    # 不允许把最后一个管理员降级，否则项目没人能管
    if member.role == "admin" and role != "admin":
        admins = (
            db.query(ProjectMember)
            .filter(ProjectMember.project_id == pid, ProjectMember.role == "admin")
            .count()
        )
        if admins <= 1:
            raise HTTPException(400, "项目至少要保留一个管理员")

    member.role = role
    audit(db, user.id, "member.role", f"project={pid}", f"uid={uid} -> {role}")
    db.commit()
    return {"ok": True}


@router.delete("/projects/{pid}/members/{uid}")
def remove_member(pid: int, uid: int, user: User = Depends(current_user),
                  db: Session = Depends(get_db)):
    require_role(db, user, pid, "admin")
    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == pid, ProjectMember.user_id == uid)
        .first()
    )
    if member is None:
        raise HTTPException(404, "成员不存在")
    if member.role == "admin":
        admins = (
            db.query(ProjectMember)
            .filter(ProjectMember.project_id == pid, ProjectMember.role == "admin")
            .count()
        )
        if admins <= 1:
            raise HTTPException(400, "项目至少要保留一个管理员")
    db.delete(member)
    audit(db, user.id, "member.remove", f"project={pid}", f"uid={uid}")
    db.commit()
    return {"ok": True}


@router.get("/projects/{pid}/audit")
def audit_list(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(db, user, pid, "admin")
    rows = (
        db.query(AuditLog, User)
        .join(User, User.id == AuditLog.actor_id)
        .order_by(AuditLog.id.desc())
        .limit(100)
        .all()
    )
    return [
        {"id": a.id, "actor": u.name, "action": a.action, "target": a.target,
         "detail": a.detail, "at": a.created_at.isoformat() if a.created_at else None}
        for a, u in rows
    ]
