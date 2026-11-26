"""把基线用例写入数据库（按 method+path 匹配接口）。"""
from sqlalchemy.orm import Session

from ..fixtures import GOLDEN_CASES
from ..models import Case, Endpoint
from .generator import fingerprint


def insert_golden_cases(db: Session, project_id: int) -> int:
    endpoints = db.query(Endpoint).filter(Endpoint.project_id == project_id).all()
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
        db.add(
            Case(
                endpoint_id=ep.id,
                name=item["name"],
                dimension=item["dimension"],
                request=request,
                expect=item["expect"],
                source="manual",
                fingerprint=fp,
            )
        )
        added += 1
    db.commit()
    return added
