"""5 份岗位定制简历（v3：统一事实 + 背景-动作-结果 + 公开基准）。"""
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT_DIR = Path(r"D:\项目\简历\v7")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_CN = "微软雅黑"
NAME = "【姓名】"
PHONE = "【手机号】"
EMAIL = "【邮箱】"
GITHUB = "github.com/hanling-UI"
GH_NOTE = "github.com/hanling-UI（两个项目均含完整 README 与本地一键运行步骤）"
SCHOOL = "中央民族大学"
MAJOR = "软件工程 · 本科"
PERIOD_EDU = "2024.09 — 2028.06（2028 届）"
AVAIL = "可实习：2026.12 起，每周 4-5 天，连续 3 个月以上"

P_A_TIME = "2026.10 — 2026.11"
P_B_TIME = "2026.09 — 2026.10"

BG_A = "背景：自测一个 22 接口的项目时，手写 40+ 条用例、逐条判断失败归属要花大半天，重复且容易漏。"
RES_A = "结果：预埋 3 缺陷全部检出、人工复核后误报 0，46 条用例 0.9 秒跑完——把「写用例 + 判责」从小时级压到分钟级。"

BG_B = "背景：原项目仅单一向量检索，编号 / 专有名词匹配差，且缺少可量化评测。"
RES_B = "结果：上下文压缩 93%（25492→1703 字符），语义覆盖（输出块与标准答案的最大余弦相似度）0.712→0.764；重排额外 +260ms；5 查询×3 要点小样本，只作趋势结论。"

PUBLIC_BENCH = "公开集回归：Petstore 规范 19 接口生成 30 条只读用例，发现 3 处「声明需鉴权但实际放行」与 2 处 5xx（官方 demo 环境，需人工复核），并修复了解析器 security 继承缺陷"

COOP = [
    "课程小组「在线网课平台」（4 人）：负责前端页面实现与接口字段对齐，参与需求评审，按组内约定接口联调",
]


def _set_font(run, size=9.5, bold=False, color=None):
    run.font.name = FONT_CN
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)


def _tight(p, before=0, after=0.8, line=1.05):
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    return p


def _bottom_border(p):
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "333333")
    pBdr.append(bottom)
    pPr.append(pBdr)


def section(doc, title):
    p = doc.add_paragraph()
    _tight(p, before=5, after=2)
    _set_font(p.add_run(title), 10.5, True)
    _bottom_border(p)


def line(doc, left, right=None, size=9.5, bold_left=True):
    p = doc.add_paragraph()
    _tight(p, before=2, after=1)
    _set_font(p.add_run(left), size, bold_left)
    if right:
        p.add_run("\t")
        _set_font(p.add_run(right), size, False)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(17), 2)
    return p


def text(doc, s, size=9, color=None):
    p = doc.add_paragraph()
    _tight(p, before=0, after=1)
    _set_font(p.add_run(s), size, False, color)
    return p


def bullet(doc, s, size=9):
    p = doc.add_paragraph(style="List Bullet")
    _tight(p, before=0, after=1)
    p.paragraph_format.left_indent = Cm(0.55)
    p.paragraph_format.first_line_indent = Cm(-0.35)
    _set_font(p.add_run(s), size)
    return p


def header(doc, intent, avail=None):
    p = doc.add_paragraph()
    _tight(p, after=0)
    _set_font(p.add_run(NAME), 20, True)

    p2 = doc.add_paragraph()
    _tight(p2, before=2, after=0)
    _set_font(p2.add_run(intent), 10.5, False, (0x33, 0x33, 0x33))

    p3 = doc.add_paragraph()
    _tight(p3, before=2, after=0)
    _set_font(p3.add_run(f"{PHONE}    {EMAIL}    北京"), 9, False, (0x59, 0x59, 0x59))

    p4 = doc.add_paragraph()
    _tight(p4, before=1, after=0)
    _set_font(p4.add_run(f"GitHub：{GH_NOTE}"), 9, False, (0x59, 0x59, 0x59))

    p5 = doc.add_paragraph()
    _tight(p5, before=0, after=2)
    _set_font(p5.add_run(avail or AVAIL), 9, False, (0x33, 0x33, 0x33))


def education(doc):
    section(doc, "教育背景")
    line(doc, f"{SCHOOL}    {MAJOR}", PERIOD_EDU, 10)
    bullet(doc, "主修课程：Python、数据结构与算法、数据库系统原理、软件工程、操作系统")
    bullet(doc, "英语：CET-【4/6】，可阅读英文技术文档与论文")


def skills(doc, pairs):
    section(doc, "专业技能")
    for cat, txt in pairs:
        p = doc.add_paragraph(style="List Bullet")
        _tight(p, after=1)
        p.paragraph_format.left_indent = Cm(0.55)
        p.paragraph_format.first_line_indent = Cm(-0.35)
        _set_font(p.add_run(f"{cat}："), 9.5, True)
        _set_font(p.add_run(txt), 9.5)


ROLES = {}

# ---------------- 01 安全 Agent ----------------
ROLES["01-安全Agent研发"] = dict(
    intent="求职意向：Agent 开发实习生（安全方向）",
    a_extra=["权限校验前置：四角色 RBAC 逐接口校验，越权返回 403；提交前强制人工确认，写操作不可绕过；操作全量留痕",
             "脱敏与异常：失败响应截断后入库；单请求超时 10s、失败重试、单条失败不影响整批",
             "踩坑复盘：鉴权 Cookie 失效、重定向误判为失败、模型输出格式漂移，均已在代码与文档中固化处理",
             "可复现与部署：docker compose 一键启动（含被测 mock），首次启动自动建账号与示例数据；"
             "线上用 Render + Neon 部署，具备独立上线能力"],
    b_extra=[],
    bench=True,
    skills=[
        ("后端与安全", "Python / FastAPI / PostgreSQL（测试 Agent 项目）；JWT 鉴权、RBAC、审计与脱敏"),
        ("Agent 编排", "LangGraph 工作流、工具调用、多轮上下文管理、人工确认、中断恢复（测试 Agent 项目）"),
        ("检索", "pgvector + BM25 双路召回、RRF 融合、Cross-Encoder 重排（RAG 项目）"),
        ("评测", "缺陷集构建、检出率 / 误报率统计、公开规范回归（测试 Agent 项目）"),
        ("工程与部署", "Docker 容器化、云平台部署（Render + Neon）、启动自举与健康检查（两个项目均独立上线过）"),
        ("工具", "习惯用大模型做代码生成、Review 与排障；能快速读源码定位问题"),
    ],
)

# ---------------- 02 平台研发 ----------------
ROLES["02-Agent平台全栈"] = dict(
    intent="求职意向：Agent 平台全栈研发实习生",
    a_extra=["后端建模：PostgreSQL 九张表（用户 / 项目 / 成员 / 接口 / 用例 / 跑批 / 结果 / 缺陷 / 审计），接口层 FastAPI + JWT 鉴权",
             "流式输出：FastAPI StreamingResponse + 前端 ReadableStream，执行进度实时推送，长任务不阻塞页面",
             "结构化输出：JSON Schema 约束模型输出并做归一化校验，非法结果丢弃，避免脏数据入库",
             "上下文与状态：接口 schema 摘要注入、失败上下文截断；checkpointer 持久化任务状态，支持中断恢复",
             "可复现与部署：docker compose 一键启动，首次启动自动建账号与示例数据；线上用 Render + Neon 部署"],
    b_extra=[],
    bench=True,
    skills=[
        ("后端", "Python / FastAPI / PostgreSQL / Docker（测试 Agent 项目：接口层、异步任务、九表建模）"),
        ("LLM 工程", "SSE 流式输出、JSON Schema 结构化输出、工具调用、上下文压缩（测试 Agent 项目）"),
        ("编排", "LangGraph 工作流与条件分支、checkpointer 状态恢复（测试 Agent 项目）"),
        ("评测", "数据集构建、批量执行、检出率 / 误报率报告（测试 Agent 项目）"),
        ("前端", "原生 HTML / CSS / JS 消费 SSE 并实时渲染（两个项目的前端页面均为自己实现，含登录、列表、报告页）"),
    ],
)

# ---------------- 03 社区增长 ----------------
ROLES["03-Agent开发-社区增长"] = dict(
    intent="求职意向：Agent 开发实习生（后端方向）",
    a_extra=["后端实现：FastAPI 接口层 + PostgreSQL 九张表（用例 / 跑批 / 结果 / 缺陷 / 审计），JWT 鉴权与四角色 RBAC",
             "业务落地：把「生成用例 → 执行 → 归因 → 提单」做成可调用接口，跑批异步化（立即返回 run_id + SSE 推进度）",
             "并发执行：asyncio + Semaphore 限并发，46 条用例 0.9 秒跑完；单请求超时 10s、失败重试",
             "可复现与部署：docker compose 一键启动，首次启动自动建账号与示例数据；线上用 Render + Neon 部署"],
    b_extra=[],
    bench=False,
    skills=[
        ("后端", "Python / FastAPI / PostgreSQL / Docker；接口设计、数据建模、JWT 鉴权、RBAC（测试 Agent 项目）"),
        ("并发", "asyncio + Semaphore 并发控制、超时重试、连接复用；数据结构与算法基础（测试 Agent 项目）"),
        ("Agent", "LangGraph 工作流与工具调用，把模型能力接到真实接口流程（测试 Agent 项目）"),
        ("检索", "BM25 + 向量混合检索、RRF 融合、重排（RAG 项目）"),
        ("工具", "习惯用大模型辅助编码与排障，提升研发效率"),
    ],
)

# ---------------- 04 引擎架构 ----------------
ROLES["04-Agent引擎架构"] = dict(
    intent="求职意向：AI Agent 研发实习生（引擎架构）",
    avail_override="可实习：2026.12 起，每周 4-5 天，连续 6 个月以上（至 2027.06，课表已排开）",
    a_extra=["稳定性：单请求超时 10s、失败重试、批量任务隔离（单条失败不影响整体），避免雪崩",
             "可观测：把每次请求、响应、耗时、断言结果封装成可查询 trace，问题可原样复现；/health 暴露数据库连通性",
             "治理与编排：RBAC 逐接口校验、操作审计、提单前人工确认；状态图 + checkpointer 支持中断恢复",
             "可复现与部署：docker compose 一键启动，首次启动自动建账号与示例数据；线上用 Render + Neon 部署"],
    b_extra=[],
    bench=True,
    skills=[
        ("稳定性", "超时控制、失败重试、并发限流、任务隔离、健康检查（测试 Agent 项目）"),
        ("可观测", "逐请求 trace、审计日志、错误分类与归因（测试 Agent 项目）"),
        ("编排与状态", "LangGraph 状态图 + checkpointer，上下文压缩，中断恢复（测试 Agent 项目）"),
        ("工程化", "Docker 容器化、服务部署、日志排查（两个项目均自己部署上线）"),
    ],
)

# ---------------- 05 交互实验室 ----------------
ROLES["05-Agent交互实验室"] = dict(
    intent="求职意向：Agent 实习生（交互实验室 · 工程方向）",
    a_extra=["从 0 到 1：独立完成需求拆解、方案设计、编码、部署与评测，不是只做某个模块",
             "端到端闭环：支持 OpenAPI / Postman 集合 / cURL 三种接入，跑完自动归因并生成缺陷草稿，人工确认后提交",
             "工程判断：明确划出「不做什么」（不做 UI 自动化、不做压测），在 README 记录取舍理由",
             "可复现与部署：docker compose 一键启动，首次启动自动建账号与示例数据；线上用 Render + Neon 部署"],
    b_extra=[],
    bench=True,
    skills=[
        ("端到端交付", "需求拆解 → 方案 → 编码 → 部署 → 评测的完整闭环（两个项目均为自己从零到上线）"),
        ("Agent 编排", "LangGraph 工作流、多工具编排、人工确认、checkpointer 状态恢复（测试 Agent 项目）"),
        ("评测", "缺陷集设计、检出率 / 误报率统计、失败案例归因（测试 Agent 项目）"),
        ("原型能力", "原生 HTML / CSS / JS + SSE 实时渲染，能独立做出可演示的原型（两个项目的前端）"),
        ("工具", "用大模型辅助需求拆解、编码与排障，快速验证想法"),
    ],
)


def projects(doc, cfg):
    section(doc, "项目经历")

    line(doc, "AI 接口测试 Agent（个人项目）", P_A_TIME, 10)
    text(doc, "技术栈：Python · FastAPI · LangGraph · PostgreSQL · httpx · Docker · 通义千问", 9, (0x59, 0x59, 0x59))
    text(doc, BG_A)
    for b in cfg["a_extra"]:
        bullet(doc, b)
    if cfg["bench"]:
        bullet(doc, PUBLIC_BENCH)
    text(doc, RES_A, 9.5, (0x33, 0x33, 0x33))

    doc.add_paragraph()
    line(doc, "RAG 混合检索系统（基于 gpt-researcher 二创）", P_B_TIME, 10)
    text(doc, "技术栈：Python · FastAPI · PostgreSQL + pgvector · BM25 · RRF · Cross-Encoder", 9, (0x59, 0x59, 0x59))
    text(doc, BG_B)
    bullet(doc, "检索链路：pgvector 存 1024 维向量（HNSW），BM25 与向量双路召回，手写 RRF（k=60）融合，再接 Cross-Encoder 重排")
    bullet(doc, "工程：FastAPI + SSE 流式输出，访问口令与每日次数限额，Docker 部署；本地一键复现，不依赖托管服务")
    for b in cfg["b_extra"]:
        bullet(doc, b)
    text(doc, RES_B, 9.5, (0x33, 0x33, 0x33))


def build(role_name, cfg):
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(1.1)
    sec.bottom_margin = Cm(1.1)
    sec.left_margin = Cm(1.7)
    sec.right_margin = Cm(1.7)

    normal = doc.styles["Normal"]
    normal.font.name = FONT_CN
    normal.font.size = Pt(9.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)

    header(doc, cfg["intent"], cfg.get("avail_override"))
    education(doc)
    projects(doc, cfg)
    skills(doc, cfg["skills"])

    section(doc, "协作与其他")
    for c in COOP:
        bullet(doc, c)

    path = OUT_DIR / f"简历-{role_name}.docx"
    doc.save(path)
    return path


for name, cfg in ROLES.items():
    print("已生成:", build(name, cfg))
