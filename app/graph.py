"""LangGraph 编排：执行 → 归因 → 生成草稿 → 等待人工确认。

为什么要图：
1. 有中断点（提单前必须人确认），图自带 interrupt_before
2. 每步有独立的输入输出，出问题能定位到节点
3. 以后要加「用例重跑」「失败重试」分支，加条边就行
"""
import logging
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph

from .services import pipeline

logger = logging.getLogger(__name__)


class RunState(TypedDict, total=False):
    run_id: int
    actor_id: int
    total: int
    passed: int
    failed: int
    bugs: int
    drafts: int


async def node_execute(state: RunState) -> dict:
    return await pipeline.execute_phase(state["run_id"])


async def node_triage(state: RunState) -> dict:
    return await pipeline.triage_phase(state["run_id"])


def node_draft(state: RunState) -> dict:
    return {"drafts": pipeline.draft_phase(state["run_id"], state["actor_id"])}


def node_confirm(state: RunState) -> dict:
    from .db import SessionLocal
    from .models import Run

    db = SessionLocal()
    try:
        run = db.get(Run, state["run_id"])
        if run:
            run.status = "done"
            db.commit()
    finally:
        db.close()
    return {}


def build_graph():
    builder = StateGraph(RunState)
    builder.add_node("execute", node_execute)
    builder.add_node("triage", node_triage)
    builder.add_node("draft", node_draft)
    builder.add_node("confirm", node_confirm)

    builder.set_entry_point("execute")
    builder.add_edge("execute", "triage")
    builder.add_edge("triage", "draft")
    builder.add_edge("draft", "confirm")
    builder.add_edge("confirm", END)

    return builder.compile(
        checkpointer=InMemorySaver(),
        interrupt_before=["confirm"],
    )


GRAPH = build_graph()


def thread_config(run_id: int) -> dict:
    return {"configurable": {"thread_id": f"run-{run_id}"}}


async def start_run(run_id: int, actor_id: int) -> None:
    """跑到 interrupt 为止（此时草稿已生成，等确认）。"""
    await GRAPH.ainvoke(
        {"run_id": run_id, "actor_id": actor_id},
        thread_config(run_id),
    )


async def resume_run(run_id: int) -> None:
    """人工确认后，从断点继续，把状态置为 done。"""
    await GRAPH.ainvoke(None, thread_config(run_id))
