"""一次完整跑批：执行 → 归因 → 生成缺陷草稿。

这是纯函数式的编排（不依赖 LangGraph），graph.py 会复用它；
万一图编排出问题，API 可以退回这里，保证演示不中断。
"""
import time
from datetime import datetime, timezone

from ..db import SessionLocal
from ..models import Case, Endpoint, Issue, Project, Run, RunItem
from .executor import execute_run
from .issues import build_issue
from .triage import triage_failures


def _now():
    return datetime.now(timezone.utc)


def prepare_run(run_id: int) -> tuple[Run, Project] | tuple[None, None]:
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is None:
            return None, None
        project = db.get(Project, run.project_id)
        run.status = "running"
        db.commit()
        db.refresh(run)
        return run, project
    finally:
        db.close()


async def execute_phase(run_id: int) -> dict:
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        project = db.get(Project, run.project_id)
        started = time.perf_counter()
        await execute_run(db, run, project.base_url, project.auth_token or "", project.custom_headers or {})
        run.duration_ms = int((time.perf_counter() - started) * 1000)
        db.commit()
        return {"total": run.total, "passed": run.passed, "failed": run.failed}
    finally:
        db.close()


async def triage_phase(run_id: int) -> dict:
    db = SessionLocal()
    try:
        rows = (
            db.query(RunItem, Case, Endpoint)
            .join(Case, Case.id == RunItem.case_id)
            .join(Endpoint, Endpoint.id == Case.endpoint_id)
            .filter(RunItem.run_id == run_id, RunItem.status != "passed")
            .all()
        )
        payload = [
            {
                "run_item_id": item.id,
                "case_name": case.name,
                "method": ep.method,
                "path": ep.path,
                "want_status": int((case.expect or {}).get("status", 200)),
                "got_status": item.resp_status,
                "resp_body": item.resp_body,
            }
            for item, case, ep in rows
        ]
        if not payload:
            return {"bugs": 0, "case_errors": 0, "env": 0}

        verdicts = await triage_failures(payload)
        by_id = {v["run_item_id"]: v for v in verdicts}
        bugs = 0
        for item, _case, _ep in rows:
            v = by_id.get(item.id)
            if not v:
                continue
            item.verdict = v["verdict"]
            item.verdict_reason = v["reason"]
            if v["verdict"] == "bug":
                bugs += 1
        db.commit()
        return {
            "bugs": bugs,
            "case_errors": sum(1 for v in verdicts if v["verdict"] == "case_error"),
            "env": sum(1 for v in verdicts if v["verdict"] == "env"),
        }
    finally:
        db.close()


def draft_phase(run_id: int, actor_id: int) -> int:
    """为判定为 bug 的失败项生成缺陷草稿，返回条数。"""
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        rows = (
            db.query(RunItem, Case, Endpoint)
            .join(Case, Case.id == RunItem.case_id)
            .join(Endpoint, Endpoint.id == Case.endpoint_id)
            .filter(RunItem.run_id == run_id, RunItem.verdict == "bug")
            .all()
        )
        created = 0
        for item, case, ep in rows:
            exists = db.query(Issue).filter(Issue.run_item_id == item.id).first()
            if exists:
                continue
            data = build_issue(
                run.project_id, run.id, item, case, ep,
                item.verdict, item.verdict_reason, "high", actor_id,
            )
            db.add(Issue(**data))
            created += 1
        run.status = "awaiting_confirm" if created else "done"
        run.finished_at = _now()
        db.commit()
        return created
    finally:
        db.close()


async def execute_and_analyze(run_id: int, actor_id: int) -> dict:
    """完整流程（无图版）：执行 → 归因 → 草稿。"""
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        run.status = "running"
        db.commit()
    finally:
        db.close()

    stats = await execute_phase(run_id)
    verdicts = await triage_phase(run_id)
    drafts = draft_phase(run_id, actor_id)
    return {**stats, **verdicts, "drafts": drafts}
