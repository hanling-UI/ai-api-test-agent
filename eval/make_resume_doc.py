"""生成《项目二总结-简历版.docx》。"""
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

OUT = r"D:\项目\项目二总结-简历版.docx"
FONT = "微软雅黑"

doc = Document()

# 全局中文字体
style = doc.styles["Normal"]
style.font.name = FONT
style.font.size = Pt(10.5)
style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

for name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
    st = doc.styles[name]
    st.font.name = FONT
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)


def h(text, level=1):
    p = doc.add_heading(text, level=level)
    return p


def para(text, bold=False, color=None, size=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.font.name = FONT
    run.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    if color:
        run.font.color.rgb = RGBColor(*color)
    if size:
        run.font.size = Pt(size)
    return p


def bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_prefix:
        r = p.add_run(bold_prefix)
        r.bold = True
        r.font.name = FONT
        r.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    r2 = p.add_run(text)
    r2.font.name = FONT
    r2.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    return p


def table(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    hdr = t.rows[0].cells
    for i, htext in enumerate(headers):
        hdr[i].text = htext
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.name = FONT
                r.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
            for p in cells[i].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9.5)
                    r.font.name = FONT
                    r.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = w
    doc.add_paragraph()
    return t


# ---------------- 标题 ----------------
title = doc.add_heading("项目二：AI 接口测试 Agent —— 简历版总结", level=0)
for r in title.runs:
    r.font.name = FONT
    r.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

para("用途：① 直接粘进简历；② 面试前 10 分钟速览；③ 被追问时按「问答库」回答。",
     color=(0x86, 0x90, 0x9C), size=9.5)

# ---------------- 一、简历填写稿 ----------------
h("一、简历填写稿（直接复制）")

para("项目名称", bold=True)
para("AI 接口测试 Agent（独立开发）")

para("技术栈", bold=True)
para("Python · FastAPI · LangGraph · PostgreSQL · SSE · httpx · Docker · 通义千问（qwen-flash / qwen-plus）")

para("项目时间", bold=True)
para("2026.11（约 4 天完成设计、开发、部署与验证）")

para("项目描述", bold=True)
para("一个面向接口层的自动化测试 Agent：输入一个接口服务（OpenAPI / Postman 集合 / cURL 任选），"
     "自动生成测试用例、并发执行并断言，对失败结果做归因（接口缺陷 / 用例错误 / 环境问题），"
     "在人工确认后生成并提交缺陷单。", )

para("业绩（四条）", bold=True)
bullet("支持 OpenAPI、Postman 集合、cURL、口令鉴权四种接入方式；"
       "自动探测 openapi.json / v3/api-docs / swagger.json / apispec_1.json 等 6 种文档路径，"
       "并在导入时排除登录、静态、文档类非业务接口，避免噪声用例。",
       "接入层：")
bullet("基于接口 Schema 按正常 / 边界 / 异常 / 鉴权 / 幂等 / 并发六维度生成用例，"
       "以 JSON Schema 约束模型输出并做指纹去重；默认只覆盖只读接口，防止自动化误触发写操作与计费接口。",
       "用例生成：")
bullet("asyncio + Semaphore 并发执行（超时、重试、跟随重定向），逐条记录请求-响应-断言 trace；"
       "归因采用「规则优先 + 模型解释」：5xx 判缺陷、401↔200 判鉴权绕过、其余 4xx 判用例问题，"
       "判定不交给概率模型，保证结论可复现。",
       "执行与归因：")
bullet("用 LangGraph 编排「执行 → 归因 → 生成缺陷草稿 →（interrupt）人工确认 → 提交」，"
       "提单前必须人工确认；提交动作全量审计；四角色 RBAC（系统管理员 / 项目 admin / tester / viewer）"
       "前端隐藏 + 后端校验双保险，绕过前端直接调 API 同样返回 403。",
       "人机协同与治理：")

para("量化数据", bold=True)
table(
    ["验证场景", "用例数", "通过", "失败", "检出缺陷", "误报", "结论"],
    [
        ["内置示例商城（预埋 3 个缺陷）", "46", "23", "23", "3 / 3", "0", "3 个预埋缺陷全部命中"],
        ["真实项目 RAG 检索系统（22 接口）", "41", "11", "30", "0", "0", "无 5xx；30 条失败均为用例虚构 ID 导致的 404"],
    ],
    widths=None,
)

para("项目链接", bold=True)
para("GitHub：https://github.com/hanling-UI/ai-api-test-agent")
para("在线 Demo：https://ai-api-test-agent.onrender.com")
para("演示账号：admin@demo.com / tester@demo.com / viewer@demo.com，密码均 demo1234（免费实例冷启动约 1 分钟）")

# ---------------- 二、面试问答 ----------------
h("二、面试追问答法（12 问）")

qa = [
    ("你这个项目算什么？和 Postman / Apifox 有什么区别？",
     "属于接口层的自动化测试辅助工具，覆盖「用例生成 → 执行 → 失败归因 → 提单」这一段。"
     "Postman / Apifox 是「人写请求、人看结果」；我这个是「从文档或一条 curl 自动出用例，"
     "跑完自动判断失败该由谁负责」，人只做两件事：审用例、确认提单。"),

    ("为什么不用 OpenAPI 就必须能测？",
     "接入支持四条路：OpenAPI 文档、Postman 集合、粘贴 cURL、以及需要口令的服务。"
     "cURL 是最贴近测试日常的输入——测试同学手上经常只有一条从浏览器 F12 复制出来的请求，"
     "所以我做了 cURL 解析：解析出方法、路径、参数、请求体、鉴权头，直接建接口并生成 2 条可执行基线用例，"
     "不依赖任何文档。"),

    ("失败归因怎么做的？为什么规则优先？",
     "先规则后模型。规则负责判定：返回 5xx 而期望 4xx → 接口缺陷；期望 401 却返回 200 → 鉴权可绕过；"
     "返回 401/403 → 环境问题（Cookie 缺失或过期）；其余 4xx 不一致 → 用例写错。"
     "模型只负责把原因写成人话。这样判定稳定可复现，模型抽风也不会把结论带偏。"),

    ("为什么 400 和 422 视为等价？",
     "两者都表示「参数不合法」，具体由框架决定（FastAPI 用 422，很多服务用 400）。"
     "统一按 400/422 等价处理，能避免大量无意义误报——这类差异不代表接口有缺陷。"),

    ("LangGraph 在这里到底做了什么？",
     "编排决策流：执行 → 归因 → 生成缺陷草稿 → interrupt（等人工确认）→ 提交。"
     "用它是因为有三个真实需求：中断恢复、提单前的人工确认节点、每个节点的输入输出可观测。"
     "但批量执行我没有塞进图里——那是并发任务，交给 asyncio，图和并发混在一起状态会爆炸。"),

    ("并发怎么做的？会不会把服务打挂？",
     "asyncio + Semaphore 限并发（默认 5），每条用例有超时（默认 10s）和重试，"
     "并且默认只生成只读接口的用例，避免自动化误触发写操作或计费接口。"),

    ("怎么保证生成的用例不是一堆垃圾？",
     "三层：① 用 JSON Schema 约束模型输出结构；② 生成后校验（方法路径必须与接口一致、状态码必须在 100-599）；"
     "③ 指纹去重（接口 + 维度 + 请求体哈希），同一条不重复入库；④ 另有人工维护的基线用例兜底，"
     "保证已知缺陷每次都被覆盖。"),

    ("你说的「检出 3/3、误报 0」怎么算的？",
     "内置 mock 服务里预埋 3 个缺陷（缺字段返回 500、鉴权可绕过、负数参数未校验），"
     "跑 46 条用例后 3 个全部被判定为 bug 并生成缺陷草稿；误报指「判定为 bug 但实际是用例问题」，统计为 0。"),

    ("真实项目那 30 条失败怎么解释？",
     "那是我另一个 RAG 项目的 22 个接口，跑 41 条用例：0 个 5xx，说明服务端没有崩溃类缺陷；"
     "30 条失败是 404，原因是用例里用了虚构的 ID（用例之间没有数据传递）。"
     "这恰好验证了归因的价值——把「测试数据缺失」和「接口缺陷」分开，而不是一律算 bug。"),

    ("权限怎么设计的？怎么证明没有越权？",
     "四角色：系统管理员（建项目、看全部）、项目 admin（项目内全部 + 成员）、tester（导入/生成/执行/提单）、"
     "viewer（只读）。前端按角色隐藏按钮，后端每个接口再校验一次 require_role。"
     "实际测试：viewer 调执行接口返回 403、调成员接口返回 403、提交缺陷返回 403。"),

    ("这个项目最难的地方是什么？",
     "归因。一开始我把所有失败都当 bug，结果跑真实项目时 30 多条全是 404，报告毫无参考价值。"
     "后来改成规则优先 + 区分环境/数据/缺陷三类，并把 400/422 视为等价、把 401/403 判为环境问题，"
     "报告才变得可用。这件事让我理解了「测试工具的价值不是多报错，而是让人相信它的结论」。"),

    ("如果让你继续做，下一步做什么？",
     "三件事：① 测试数据关联——用 JSONPath 从上一个接口的响应里取真实 ID 注入后续用例，消除 404 噪声；"
     "② checkpointer 换成 Postgres，支持容器重启后恢复未完成的跑批；"
     "③ 接入 CI（GitHub Action），每次提交自动跑回归。"),
]
for i, (q, a) in enumerate(qa, 1):
    p = doc.add_paragraph()
    r = p.add_run(f"Q{i}. {q}")
    r.bold = True
    r.font.name = FONT
    r.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    p2 = doc.add_paragraph()
    r2 = p2.add_run(f"答：{a}")
    r2.font.name = FONT
    r2.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

# ---------------- 三、设计取舍 ----------------
h("三、设计取舍（面试官会认可的点）")
table(
    ["决策", "理由"],
    [
        ["归因规则优先、模型只写解释", "判定必须稳定可复现；5xx、401↔200 这类信号不应交给概率模型"],
        ["400 / 422 视为等价", "都属于参数不合法，框架选哪个不代表接口有缺陷"],
        ["默认只生成只读接口用例", "避免自动化误触发计费/写操作；需要时显式关闭"],
        ["人工基线用例 + 模型生成并行", "模型不保证命中已知缺陷，基线用例兜底"],
        ["LangGraph 只管决策流", "中断恢复 + 确认节点 + 可观测；批量执行交给 asyncio"],
        ["导入时排除登录/静态/文档接口", "它们是基础设施不是业务 API，生成用例只会产生噪声"],
        ["前端原生 JS 无构建", "部署简单，clone 即跑，便于面试官验证"],
    ],
)

# ---------------- 四、演示脚本 ----------------
h("四、60 秒演示脚本")
bullet("打开 Demo → admin 登录 → 看到「示例商城 API」项目（12 接口）")
bullet("「接口与用例」→ 展示 6 维度用例标签（正常/边界/异常/鉴权）")
bullet("「执行与报告」→ 运行全部用例 → 进度条实时推进（SSE）")
bullet("点「失败」筛选 → 展开一条 5xx 失败 → 看请求、响应、断言 diff、复现 curl")
bullet("「缺陷」→ 3 条草稿（正是预埋的 3 个 bug）→ 勾选 → 确认提交 → 状态变 submitted")
bullet("用 viewer 登录 → 写操作按钮消失，直接调接口返回 403")
bullet("「统计」→ 检出 3、误报 0、覆盖率 100%")

# ---------------- 五、边界 ----------------
h("五、已知边界（主动说明，别等被问穿）")
bullet("用例之间没有数据传递，详情类接口用虚构 ID 会产生 404 噪声（下一版做 JSONPath 变量提取）")
bullet("LangGraph 状态存在进程内存，容器重启后未确认的跑批需重跑（生产应换 Postgres checkpointer）")
bullet("未覆盖 UI 自动化、性能压测、契约测试、CI 定时调度")
bullet("演示账号为环境变量配置，生产应接入企业 SSO / OIDC")

# ---------------- 六、与其他项目分工 ----------------
h("六、两个项目怎么分工（避免面试官觉得重复）")
table(
    ["", "项目一：RAG 检索系统", "项目二：接口测试 Agent"],
    [
        ["解决的问题", "检索质量（召回、排序、评测）", "测试效率（出题、执行、判责、提单）"],
        ["技术重点", "混合检索、RRF、重排、离线评测", "工具编排、并发执行、规则归因、人机确认"],
        ["有无副作用", "只读，产出报告", "会真的发请求、真的提单"],
        ["面试讲什么", "讲检索深度与评测方法", "讲工程完整性与判责逻辑"],
    ],
)

# ---------------- 七、风险提示 ----------------
h("七、风险提示（自己心里有数）")
bullet("别说「支持所有协议/所有场景」——只做 HTTP 接口，UI 和性能没做")
bullet("别说「AI 自动判断百分百准确」——归因是规则优先 + 模型解释，仍有边界，要靠人工复核")
bullet("别把 mock 的 3 个缺陷说成「真实项目发现的」——那是预埋用例，诚实说是演示数据")
bullet("被问「能测生产吗」：默认只读接口 + 环境标记（prod 禁止跑批），但仍建议只对测试环境使用")

para("")
para("—— 以上数据均来自本地与线上实测，可当场演示。", color=(0x86, 0x90, 0x9C), size=9.5)

doc.save(OUT)
print("已生成:", OUT)
