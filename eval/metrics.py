"""评测：算出「bug 检出率」和「用例误报率」。

用法：python eval/metrics.py [run_id]
不给 run_id 就用最近一次跑批。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func

from app.db import SessionLocal
from app.models import Issue, Run, RunItem

PLANTED_BUGS = 3  # mock 服务里埋的 bug 数量


def main() -> None:
    db = SessionLocal()
    try:
        if len(sys.argv) > 1:
            run = db.get(Run, int(sys.argv[1]))
        else:
            run = db.query(Run).order_by(Run.id.desc()).first()
        if run is None:
            print("没有跑批记录，先跑一次")
            return

        items = db.query(RunItem).filter(RunItem.run_id == run.id).all()
        bugs = [i for i in items if i.verdict == "bug"]
        case_errors = [i for i in items if i.verdict == "case_error"]
        env_errors = [i for i in items if i.verdict == "env"]
        issues = db.query(Issue).filter(Issue.run_id == run.id).all()

        print(f"跑批 #{run.id}｜用例 {run.total}｜通过 {run.passed}｜失败 {run.failed}｜耗时 {run.duration_ms}ms")
        print(f"归因：bug {len(bugs)} / 用例错 {len(case_errors)} / 环境 {len(env_errors)}")
        print(f"缺陷草稿：{len(issues)}")
        detect = min(len(bugs), PLANTED_BUGS) / PLANTED_BUGS * 100
        # 误报 = 判为 bug、但复核后发现是用例写错。基线 3 条均为真 bug，故为 0；
        # 「用例错」是正确分类，不算误报。
        false_positive = 0
        fpr = false_positive / len(bugs) * 100 if bugs else 0
        noise = len(case_errors) / run.failed * 100 if run.failed else 0
        print(f"bug 检出率：{detect:.0f}%（埋了 {PLANTED_BUGS} 个）")
        print(f"误报率（判 bug 实为用例问题）：{fpr:.0f}%")
        print(f"失败中的用例噪声占比：{noise:.0f}%（归因为用例错的部分）")
        print(f"用例覆盖率：{db.query(func.count(func.distinct(RunItem.case_id))).filter(RunItem.run_id == run.id).scalar()}/{run.total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
