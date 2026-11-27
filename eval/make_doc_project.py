"""生成《项目必会知识清单》——紧凑排版，小五字号，含缺口技术教学与课后题。"""
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = r"D:\项目\项目必会知识清单.docx"
FONT = "微软雅黑"

doc = Document()
sec = doc.sections[0]
sec.top_margin = Cm(1.4)
sec.bottom_margin = Cm(1.3)
sec.left_margin = Cm(1.6)
sec.right_margin = Cm(1.6)

normal = doc.styles["Normal"]
normal.font.name = FONT
normal.font.size = Pt(9)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
normal.paragraph_format.space_before = Pt(0)
normal.paragraph_format.space_after = Pt(0)
normal.paragraph_format.line_spacing = 1.05

for nm in ("Title", "Heading 1", "Heading 2", "Heading 3"):
    st = doc.styles[nm]
    st.font.name = FONT
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    st.paragraph_format.space_before = Pt(4)
    st.paragraph_format.space_after = Pt(1)
    st.paragraph_format.line_spacing = 1.05


def _f(run, size=9, bold=False, color=None):
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)


def h1(text):
    p = doc.add_heading(text, level=1)
    for r in p.runs:
        _f(r, 13, True)
    return p


def h2(text):
    p = doc.add_heading(text, level=2)
    for r in p.runs:
        _f(r, 10.5, True)
    return p


def para(text, size=9, bold=False, color=None, indent=0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(0)
    pf.line_spacing = 1.05
    if indent:
        pf.left_indent = Cm(indent)
    _f(p.add_run(text), size, bold, color)
    return p


def bullet(text, size=9, indent=0.4):
    p = doc.add_paragraph(style="List Bullet")
    pf = p.paragraph_format
    pf.space_after = Pt(0)
    pf.line_spacing = 1.05
    pf.left_indent = Cm(indent + 0.35)
    pf.first_line_indent = Cm(-0.3)
    _f(p.add_run(text), size)
    return p


def kv(label, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(0)
    pf.line_spacing = 1.05
    pf.left_indent = Cm(0.35)
    _f(p.add_run(f"{label}："), 9, True)
    _f(p.add_run(text), 9)
    return p


def exercises(items):
    para("课后题（合上文档口述，答不上来再回看）", bold=True)
    for i, q in enumerate(items, 1):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_after = Pt(0)
        pf.line_spacing = 1.05
        pf.left_indent = Cm(0.7)
        pf.first_line_indent = Cm(-0.35)
        _f(p.add_run(f"{i}. {q}"), 9)
    doc.add_paragraph()


# ==================== 封面 ====================
t = doc.add_heading("项目必会知识清单（含缺口补强）", level=0)
for r in t.runs:
    _f(r, 18, True)
para("对应两个项目：① AI 接口测试 Agent　② RAG 混合检索系统", 9, True)
para("用法：先看章节正文 → 合上口述课后题 → 答不上的回看。第三部分是岗位要但你还没学的技术，"
     "每条都给了「面试怎么问 / 你怎么答 / 30 分钟能补的证据」。", 8.5, color=(0x59, 0x59, 0x59))
doc.add_paragraph()

# ==================== 第一部分 ====================
h1("第一部分　项目二：AI 接口测试 Agent")

h2("第 1 章　定位与业务价值")
kv("一句话", "给一个接口服务（OpenAPI / Postman / cURL 任选），自动生成用例、并发执行并断言，"
            "对失败归因（接口缺陷 / 用例错误 / 环境问题），人工确认后提交缺陷单。")
kv("用户", "测试工程师、后端自测、没有专职测试的小团队。")
kv("痛点", "自测一个 22 接口的项目时，手写 40+ 条用例、逐条判断失败归属要花大半天，重复且容易漏。")
kv("与 Postman 区别", "Postman 是人写请求、人看结果；本工具从文档或一条 curl 自动出题、自动判责，人只审用例与确认提单。")
kv("与聊天机器人区别", "有真实副作用：发 HTTP 请求、写数据库、建缺陷单，且写操作前必须人工确认。")
kv("价值", "把「写用例 + 判责」从小时级压到分钟级，并让结论可复现。")
exercises([
    "用 30 秒介绍这个项目（含用户、痛点、方案、结果）。",
    "它和 Postman / Apifox 的本质区别是什么？",
    "为什么说它不是聊天机器人？举一个它有副作用的例子。",
    "这个项目最难的地方是什么？为什么？",
    "如果面试官说「这工具没什么用」，你怎么回？",
])

h2("第 2 章　架构与一次跑批的完整链路")
kv("分层", "浏览器（原生 HTML/JS）→ FastAPI（JWT + RBAC）→ LangGraph 决策图 → asyncio 执行器 → PostgreSQL。")
kv("九张表", "users / projects / project_members / endpoints / cases / runs / run_items / issues / audit_logs。")
para("一次跑批的时序（背下来）：", bold=True)
bullet("前端 POST /api/runs，校验角色（tester 及以上），写 runs（status=pending）。")
bullet("asyncio.create_task 起后台任务，接口立即返回 run_id（不阻塞前端）。")
bullet("前端用 fetch 读 SSE 流，实时显示进度。")
bullet("图执行 execute 节点：查该项目所有启用用例。")
bullet("asyncio + Semaphore(5) 并发请求，单条超时 10s，断言后写 run_items（含 trace）。")
bullet("triage 节点：规则判归属，模型补解释。")
bullet("draft 节点：为 verdict=bug 的失败项生成缺陷草稿。")
bullet("interrupt 暂停等人确认；确认后提交并写 audit_logs。")
kv("设计取舍", "接口立即返回（异步化）+ 执行与决策分离（并发归 asyncio，决策归图）+ 全流程可观测 + 写操作可拦截。")
exercises([
    "点「运行」到出结果，中间发生了什么？按顺序说 8 步。",
    "为什么跑批接口要立即返回，而不是等跑完再返回？",
    "runs 和 run_items 是什么关系？各存什么？",
    "为什么把执行和归因分成两个节点？",
    "trace 里记了哪些字段？为什么必须记？",
])

h2("第 3 章　接入层：四种接入方式")
bullet("OpenAPI：填服务根地址，自动探测 /openapi.json、/v3/api-docs、/swagger.json、/apispec_1.json、/api-docs、/docs/openapi.json 六种路径。")
bullet("Postman 集合：上传 collection.json（v2.1），解析 item[].request 的 method / url / header / body。")
bullet("cURL：解析 -X / -H / -d / -u 与 URL，建接口并直接生成 2 条可执行基线用例。")
bullet("口令 / Cookie：POST 登录接口拿 Set-Cookie，存进项目的 custom_headers，后续请求自动携带。")
kv("非业务接口过滤", "导入时排除 /login、/logout、/static、/docs、/openapi.json、/.well-known 等，避免噪声用例。")
kv("security 继承（踩坑）", "OpenAPI 里操作级写了 security 就覆盖全局；写空数组 [] 表示公开；完全没写才继承全局。"
                          "我一开始一律按全局判，导致 Petstore 上公开接口被误判为需鉴权，产生 8 条假 bug。")
exercises([
    "服务没有 OpenAPI 文档时，你有几条路接入？分别怎么做？",
    "为什么导入时要排除 /login 这类接口？",
    "口令登录具体做了什么？拿到的 Cookie 存在哪？",
    "OpenAPI 的 security 继承规则是什么？你踩过什么坑？",
    "服务用 OAuth / 扫码登录，你还能测吗？怎么测？",
])

h2("第 4 章　用例生成：六维度 + 约束 + 去重")
kv("六维度", "normal 正常、boundary 边界、error 异常、auth 鉴权、idempotent 幂等、concurrent 并发。")
kv("Prompt 设计", "① 把接口 schema 压成摘要（字段名/类型/是否必填/枚举）喂模型；"
                "② 明确约束：不要自己生成 Authorization 头、创建类默认期望 200、400/422 都算对；③ 只输出 JSON 数组。")
kv("校验", "方法路径必须与接口一致、状态码在 100~599、字段结构归一化，不合格直接丢弃。")
kv("去重", "sha1(接口 id + 维度 + 请求体) 作为指纹，同一指纹不重复入库。")
kv("只读模式", "默认只给 GET/HEAD 生成，避免自动化误触发写操作或计费接口（如 POST /report/）。")
kv("基线用例", "人工维护 3 条（缺 name 返回 500、鉴权可绕过、page=-1 返回 500），模型不保证命中已知缺陷。")
kv("成本", "12 个接口生成 43~45 条用例，约 39 秒，约 0.01 元（qwen-flash）。")
exercises([
    "用例是怎么生成的？六维度分别测什么？",
    "怎么保证模型输出可用？三道校验是什么？",
    "为什么要指纹去重？指纹怎么算？",
    "为什么要人工基线用例？举一条。",
    "怎么防止生成用例误触发计费接口？",
])

h2("第 5 章　执行引擎：并发、断言、可观测")
kv("并发", "asyncio + Semaphore(5)；单条超时 10s；异常记为 error 而不是失败。")
kv("断言", "状态码（400/422 视为等价）、关键字段存在性、耗时上限。")
kv("跟随重定向", "httpx 默认 False，我改成 True。因为已登录访问 /login 会 303 跳首页，不跟随会误判失败——那是工具的问题。")
kv("路径参数", "把 {id} 用参数值填充，没给就填 1，避免 404 让用例整体失效。")
kv("trace", "请求体、响应状态、响应体前 4KB、耗时、断言逐项 ✅/❌，出问题可原样复现。")
kv("SSE", "FastAPI StreamingResponse + 前端 fetch 的 ReadableStream 读取（EventSource 不能带 Authorization 头）。")
kv("实测", "46 条用例并发执行约 0.7~0.9 秒。")
exercises([
    "并发怎么控制的？会不会把服务打挂？",
    "为什么 400 和 422 判等价？",
    "为什么开启 follow_redirects？不开启会怎样？",
    "一条用例失败，你怎么证明它真的失败？",
    "SSE 和 WebSocket 你选哪个？为什么？EventSource 有什么限制？",
])

h2("第 6 章　失败归因：规则优先 + 模型解释")
para("规则表（背下来）：", bold=True)
bullet("5xx，期望 4xx → bug（服务端未处理该输入）")
bullet("期望 401 却返回 200 → bug（鉴权可绕过）")
bullet("返回 401 / 403 → env（Cookie/Token 缺失或过期，先补登录态）")
bullet("请求没发出（超时/连接失败，status=0）→ env")
bullet("4xx 但不是期望值 → case_error（用例断言过死或数据不对）")
kv("为什么规则优先", "判定必须可复现、可解释；模型是概率的，一旦让它判 5xx 还是 4xx，结论会漂移，报告就不可信。")
kv("模型做什么", "只把原因写成人话（一次批量调用，失败就降级用规则文案），成本与风险都可控。")
kv("真实案例", "对真实项目 41 条用例：0 个 5xx，30 条失败全是 404（用例虚构 ID）→ 判 case_error，"
             "结论是「服务端无缺陷，失败来自测试数据缺失」。")
kv("边界", "① 需要测试数据关联（JSONPath 取真实 ID）；② 复杂业务语义仍需人工复核；"
          "③ 公开集回归时发现「规范声明需鉴权但实际放行」也判 bug，需人工确认是否规范问题。")
exercises([
    "失败归因怎么做的？五条规则各是什么？",
    "为什么不让模型直接判？",
    "401 为什么算环境问题而不是 bug？",
    "误报和漏报你怎么控制？",
    "如果提高归因准确率，下一步做什么？",
])

h2("第 7 章　LangGraph：到底用来干什么")
kv("四节点", "execute（执行）→ triage（归因）→ draft（生成缺陷草稿）→ confirm（确认后置完成）。")
kv("中断", "compile(checkpointer=InMemorySaver(), interrupt_before=['confirm'])，thread_id = run-{id}。")
kv("为什么用", "① 提单前必须停（人工确认）；② 中断可恢复；③ 每个节点输入输出可观测。")
kv("为什么不全用图", "批量执行是并发任务，塞进图里状态会爆炸；图只负责分支、循环、中断。")
kv("兜底", "图执行异常时自动降级为普通 pipeline（execute → triage → draft），保证演示不中断。")
kv("已知限制", "InMemorySaver 在进程内存，容器重启后未确认的跑批会丢；生产应换 Postgres checkpointer。")
exercises([
    "LangGraph 在你项目里承担什么？",
    "为什么执行不放进图里？",
    "interrupt 怎么实现的？恢复时调用什么？",
    "checkpointer 用的什么？有什么问题？",
    "为什么不用手写 if/else 状态机？",
])

h2("第 8 章　权限、审计与部署")
bullet("角色：系统管理员（建项目、看全部、对所有项目具备 admin）、项目 admin（成员管理）、tester（导入/生成/跑批/提单）、viewer（只读）。")
bullet("认证：JWT（HS256，2 小时过期）+ bcrypt 存密码；token 里只放 user_id，权限每次查库。")
bullet("双保险：前端按角色隐藏按钮 + 后端 require_role 逐接口校验；实测 viewer 调跑批接口 403、调成员接口 403。")
bullet("审计：登录、建项目、改地址、导入、生成、跑批、提单、成员变更、个人资料，全部落 audit_logs。")
bullet("部署：Dockerfile → start.py：容器内先起被测 mock（127.0.0.1:9000），再用 $PORT 起应用。")
bullet("线上：Render（Docker，Free）+ Neon（免费 Postgres，连接串需 postgresql+psycopg:// 与 ?sslmode=require）。")
bullet("bootstrap：首次启动自动建账号、示例项目、12 接口、4 条基线用例，幂等且不调模型（秒级、零成本）。")
exercises([
    "权限怎么做双层校验？",
    "为什么建项目只有系统管理员能建？",
    "JWT 里放了什么？为什么不放权限？",
    "线上数据库连不上怎么排查？",
    "为什么用 start.py 而不是直接 uvicorn？",
])

h2("第 9 章　评测数据与结论")
bullet("内置 mock：46 条用例，23 通过 / 23 失败，3 个预埋缺陷全部检出，误报 0。")
bullet("真实项目：22 接口、41 条用例，0 个 5xx，30 条失败均为 404（用例虚构 ID）。")
bullet("公开集：Petstore 规范 19 接口（需鉴权 9 / 公开 10），生成 30 条只读用例，发现 3 处「声明需鉴权但实际放行」"
       "与 2 处 5xx（官方 demo 环境），并修复了解析器 security 继承缺陷。")
bullet("指标定义：检出率 = 检出缺陷 / 预埋缺陷；误报率 = 判 bug 但实为用例问题 / 判 bug 总数；覆盖率 = 有用例的接口 / 总接口。")
bullet("复现：eval/smoke.py（端到端）、eval/metrics.py（检出/误报）、eval/roles.py（权限边界）、eval/curl_import.py（curl 接入）、eval/petstore_bench.py（公开集）。")
exercises([
    "3/3 检出怎么算的？",
    "真实项目 0 个 bug，是不是说明工具没用？",
    "你的误报率怎么算？样本多大？",
    "公开集回归发现了什么问题？你怎么定位的？",
    "如果面试官说「你这是自造数据自评」，你怎么回？",
])

h2("第 10 章　高频追问 20 问（速答）")
items = [
    ("一个人做的吗", "是，设计、编码、部署、评测全流程，约 5 天。"),
    ("代码量", "后端约 1800 行、前端约 900 行、mock 与评测约 300 行。"),
    ("为什么 FastAPI", "异步原生、SSE 简单、自动生成 OpenAPI、部署轻。"),
    ("前端为什么不用框架", "无构建、部署简单、clone 即跑；状态量小，原生 JS 够用。"),
    ("为什么不用 pytest 跑用例", "用例是数据驱动存在数据库里，运行时动态组装；pytest 更适合代码化用例。（已在补单测）"),
    ("怎么防止打挂生产", "项目标 env=prod 禁止跑批；默认只生成只读接口；并发受限、超时 10s。"),
    ("为什么 Postgres", "JSONB 存请求/断言结构方便；事务可靠；与 Neon 兼容。"),
    ("为什么不用 Redis", "当前量级不需要；下一步用 Redis 做跑批限流与统计缓存。"),
    ("SSE 怎么实现", "StreamingResponse 每秒推 JSON，前端 fetch 的 ReadableStream 读取。"),
    ("能中断跑批吗", "当前不能（下一版加取消令牌）；生成用例是同步等待。"),
    ("失败怎么复现", "缺陷单带 curl 和请求参数，复制即可复现。"),
    ("模型用的什么", "qwen-flash 生成用例、qwen-plus 写归因解释（OpenAI 兼容协议）。"),
    ("怎么控成本", "只对缺失用例的接口生成；指纹去重；归因只发失败上下文；全量约 0.01 元。"),
    ("输出格式错乱怎么办", "JSON 提取容错 + 结构化校验 + 丢弃非法项；仍失败就跳过该接口。"),
    ("怎么做幂等", "用例指纹去重、导入覆盖式重建、缺陷按 run_item 唯一。"),
    ("审计记了什么", "谁、何时、什么动作、对象、结果；只有管理员能看。"),
    ("多步登录怎么测", "当前支持 Cookie / 固定头；多步流程需前置脚本能力（下一版）。"),
    ("覆盖业务逻辑吗", "目前是接口契约层（状态码/字段/参数），业务规则靠人补充或用例模板——如实说。"),
    ("和公司平台怎么共存", "作为平台里的「用例生成 + 归因」模块接入，不替代调度与执行框架。"),
    ("给你一周继续做什么", "① 测试数据关联（JSONPath）② Postgres checkpointer ③ CI 集成 ④ 用例模板库。"),
]
for i, (q, a) in enumerate(items, 1):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(0)
    pf.line_spacing = 1.05
    pf.left_indent = Cm(0.7)
    pf.first_line_indent = Cm(-0.35)
    _f(p.add_run(f"{i}. {q}："), 9, True)
    _f(p.add_run(a), 9)
doc.add_paragraph()

# ==================== 第二部分 ====================
doc.add_page_break()
h1("第二部分　项目一：RAG 混合检索系统")

h2("第 1 章　定位与数据")
kv("一句话", "基于 gpt-researcher 二创：把单一向量检索升级为「关键词 + 向量 + RRF + 重排」，并用离线评测证明收益。")
kv("数据", "早期 20 篇中文文档切成 43 块；后扩到更大规模（按实际说）。")
kv("功能", "DAG 式研究流程（规划 → 检索 → 汇总 → 写报告），报告可导出 Word/MD。")

h2("第 2 章　切分策略")
kv("做法", "段落累积 + 超长硬切 + 尾部重叠；CHUNK_SIZE 200、OVERLAP 40。")
kv("真实教训", "最初 CHUNK_SIZE=500，20 篇文档每篇约 355 字，导致「一篇一块」，检索几乎失效；"
            "改 200/40 后切成 43 块，Top1 相似度从 0.5088 / 0.6453 / 0.6373 提升到 0.5725 / 0.6847 / 0.6721，噪声消失。")
exercises(["切分大小怎么定？为什么 500 不行？", "重叠的作用是什么？重叠太多会怎样？"])

h2("第 3 章　向量与 pgvector")
kv("模型与维度", "text-embedding-v4，1024 维；cosine 距离（<=>）。")
kv("索引", "vector(1024) + HNSW（vector_cosine_ops，m / ef_construction 可调）。")
kv("先扫后滤", "带严格 WHERE 的向量检索可能返回不足；解法：调高 ef_search、建部分索引、或用 pgvector 0.8 的 iterative scan。")
kv("规模化瓶颈", "30 万块 × 1024 × 4B ≈ 1.2GB 原始向量 + 图结构，内存与写入是瓶颈；可用 halfvec、分区或换 Milvus/Qdrant。")
exercises(["pgvector 的 HNSW 参数怎么调？", "什么叫先扫后滤？怎么解决？", "向量维度为什么是 1024？换模型要做什么？"])

h2("第 4 章　混合检索与 RRF")
kv("两路", "BM25（Postgres tsvector / ts_rank）负责精确匹配，向量负责语义匹配，用 RRF 融合。")
kv("公式", "score(d) = Σ 1/(k + rank_i(d))，k 常取 60。")
kv("为什么有效", "两路分数量纲不可比（BM25 无上界、余弦 0~1），只看排名就能融合，鲁棒且无需调权重。")
exercises(["RRF 公式默写。", "为什么不用加权求和？", "k=60 怎么来的？调大调小有什么影响？"])

h2("第 5 章　重排（Rerank）")
kv("流程", "粗召回 Top 50 → 交叉编码器逐对打分 → 取 Top 5。")
kv("区别", "双塔（向量）快但精度低；交叉编码器准但慢，所以只对少量候选做。")
kv("实测", "收益仅 +0.009（0.755 → 0.764），延迟 +260ms（P95）；结论：重排有用但性价比一般，数据量小时提升有限。")
exercises(["重排为什么只提升 0.009？", "什么场景值得上重排？", "双塔和交叉编码器的差别？"])

h2("第 6 章　评测方法与结果")
para("评测结果（5 条查询抽样，语义覆盖指标）：", bold=True)
bullet("none（全量塞入）：25492 字符，覆盖 0.712")
bullet("keyword（BM25）：9937 字符，0.733")
bullet("embeddings（纯向量）：10001 字符，0.742")
bullet("hybrid（RRF）：1721 字符，0.755")
bullet("hybrid + rerank：1703 字符，0.764，耗时 2.56s")
kv("关键数字", "上下文体积压缩 93%（25492 → 1703 字符），语义覆盖从 0.712 提升到 0.764。")
kv("怎么评的", "自建 5 条查询做抽样，固定温度 0 保证可复现；先看召回，再看精度，最后看忠实度。")
kv("诚实口径", "样本小（5 条），所以更强调「压缩率 93%」这个硬指标，而不是吹 P@1 的显著性。")
exercises([
    "评测集多大？为什么小样本要谨慎解读？",
    "25492 → 1703 是什么指标？不是命中数吗？",
    "为什么先看召回再看精度？",
    "如果面试官问「涨 5 个点算显著吗」，你怎么答？",
])

h2("第 7 章　高频追问 10 问")
for i, (q, a) in enumerate([
    ("为什么做混合检索", "单一向量对编号、专有名词不敏感；BM25 补精确匹配，两者互补。"),
    ("为什么用 pgvector", "数据量小、已用 Postgres，少一个组件；上量再换 Milvus。"),
    ("怎么降低幻觉", "只依据召回内容回答 + 相似度阈值拒答 + 引用原文。"),
    ("长文档怎么处理", "切块 + 重叠 + 父文档映射（小块检索、大块喂模型）。"),
    ("RAG 最常见失败原因", "召回不到（切分/检索问题），而不是模型不行。"),
    ("这个项目和项目二区别", "项目一解决检索质量（只读、产出报告）；项目二解决测试效率（有副作用、产出缺陷单）。"),
    ("你做了哪些二创", "混合检索 + RRF、重排、离线评测、访问口令与限额、报告导出。"),
    ("重做会改什么", "先建评测集再调参；切分先做实验；重排做成可开关。"),
    ("为什么不用 Milvus", "规模不需要；运维成本高。"),
    ("能扩展到多大", "百万级块需要 halfvec/分区，或换专用向量库。"),
], 1):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(0)
    pf.line_spacing = 1.05
    pf.left_indent = Cm(0.7)
    pf.first_line_indent = Cm(-0.35)
    _f(p.add_run(f"{i}. {q}："), 9, True)
    _f(p.add_run(a), 9)

# ==================== 第三部分 ====================
doc.add_page_break()
h1("第三部分　岗位要但你没学的技术（补强讲义）")
para("每条结构：是什么 → 面试会怎么问 → 你怎么答（不会也要答出迁移思路）→ 30 分钟能做的证据。", 8.5,
     color=(0x59, 0x59, 0x59))
doc.add_paragraph()

h2("1. Redis")
kv("是什么", "内存 KV 存储。五大数据结构：String（计数/缓存）、Hash（对象）、List（队列）、Set（去重/交并）、ZSet（排行榜/延时队列）。")
kv("常用场景", "缓存（旁路缓存 Cache-Aside）、分布式锁（SET NX PX + Lua 释放）、限流（INCR + EXPIRE 或令牌桶）、会话、排行榜。")
kv("面试会问", "缓存穿透/击穿/雪崩怎么解？分布式锁怎么防误删？Redis 单线程为什么快？")
kv("你怎么答", "我没在项目里用过 Redis，但我知道它在我的场景里能解决什么：① 跑批限流（每天每项目 20 次，INCR+EXPIRE）；"
            "② 统计接口缓存（ZSet 存近 N 次耗时做 P95）；③ 分布式锁防止同一 run 被重复执行（SET NX PX + 值校验后 Lua 删）。")
kv("30 分钟证据", "在项目二加一个「每日跑批次数限流」：redis.incr(key) > N 就 429，并写进 README。")
exercises(["缓存穿透/击穿/雪崩分别是什么？各自怎么解？", "用 Redis 做限流的两种写法？", "分布式锁为什么要用 Lua 释放？"])

h2("2. 消息队列（Kafka / RocketMQ）")
kv("是什么", "解耦、削峰、异步。核心概念：Topic、Partition、Offset、Consumer Group、ACK、重试与死信。")
kv("为什么测试/平台岗要", "跑批、报告生成这类长任务要异步化，队列比 BackgroundTasks 更可靠（可持久化、可重试、可水平扩展）。")
kv("面试会问", "怎么保证消息不丢？怎么保证不重复消费（幂等）？顺序消息怎么做？")
kv("你怎么答", "我项目里用 asyncio 后台任务 + DB 状态表实现异步，没上队列；如果上量，我会换成队列："
            "producer 写 run 记录后发消息，consumer 执行并更新状态，用 run_id 做幂等键，失败进重试队列、超限进死信。")
kv("30 分钟证据", "把 README 的「下一步」补一版队列设计：Topic 设计、幂等键、重试策略。")
exercises(["消息丢失的三个环节？怎么防？", "幂等消费怎么做？", "什么场景不该用队列？"])

h2("3. Dify / Coze")
kv("是什么", "低代码 LLM 应用平台：可视化编排工作流（节点 + 连线）、内置知识库、插件、发布成 API/网页。")
kv("和你项目的区别", "它们把「编排、知识库、发布」做成产品；你的项目是代码级实现，控制力更强、可定制，但搭建成本高。")
kv("面试会问", "用过 Dify/Coze 吗？和 LangChain/LangGraph 什么关系？")
kv("你怎么答", "搭过 Coze 工作流（知识库检索 → LLM 生成），理解它的节点模型；和我用 LangGraph 写的状态图是同一类东西，"
            "区别是它把工具、模型、发布都封装好了，适合快速验证；我需要自定义执行器与归因逻辑，所以用代码实现。")
kv("30 分钟证据", "注册 Coze，搭一个「输入问题 → 知识库 → 回答」工作流，截图存着；面试可展示。")
exercises(["Dify 的工作流节点和你 LangGraph 的节点差异在哪？", "什么场景适合低代码平台，什么场景必须写代码？"])

h2("4. Milvus / FAISS / pgvector 选型")
kv("是什么", "FAISS：库，本地索引（IVF/HNSW/PQ），不负责增删改与持久化；Milvus：分布式向量数据库（集合、分区、多索引）；"
          "pgvector：Postgres 扩展，和业务数据同库，事务一致。")
kv("选型逻辑", "数据量小 + 已有 PG → pgvector；百万级以上 + 高并发 → Milvus；离线实验/嵌入式 → FAISS。")
kv("面试会问", "为什么不用 Milvus？HNSW 和 IVF 区别？")
kv("你怎么答", "我用 pgvector 是因为数据量小、要和业务表 JOIN、想少一个组件；"
            "HNSW 是图索引，查询快、内存占用高、插入要维护图；IVF 是倒排聚类，需要训练、召回依赖 nprobe，内存更省。")
exercises(["HNSW 与 IVF 的取舍？", "向量库和向量索引库的区别？", "pgvector 的性能瓶颈在哪？"])

h2("5. MCP（Model Context Protocol）")
kv("是什么", "把「工具/数据源」以统一协议暴露给模型客户端的标准，类似 USB-C：Server 暴露 tools/resources/prompts，Client 连接使用。")
kv("与 Function Calling 区别", "FC 是模型侧「决定调哪个函数」的能力；MCP 是工具侧「怎么被接入」的标准。二者互补。")
kv("面试会问", "MCP 解决什么问题？和直接写工具函数有什么区别？")
kv("你怎么答", "MCP 解决的是复用与解耦：工具写一次，多个客户端/框架都能接，不用为每个 Agent 重写适配层。"
            "我没落地 MCP Server，但我的工具层（OpenAPI 解析、cURL 解析、HTTP 执行、断言）已经是「统一接口 + 描述」的结构，"
            "要包成 MCP Server 主要是加协议层。")
exercises(["MCP 的三个原语是什么？", "MCP 和 FC 的关系？", "自己写 MCP Server 最小需要什么？"])

h2("6. LangChain 与 LangGraph 的区别")
kv("定位", "LangChain：组件库（模型、提示、检索、工具）+ 链式组合；LangGraph：有状态的图编排（节点、边、checkpointer、中断）。")
kv("什么时候用哪个", "线性流程用 LangChain 够；需要分支、循环、人工中断、断点恢复就用 LangGraph。")
kv("面试会问", "为什么用 LangGraph 不用 LangChain 的 Agent？")
kv("你怎么答", "我的流程有分支（全通过 / 有失败）、有中断（提单前等人确认）、要断点恢复，LangChain 的链式结构表达不了，所以用图。")
exercises(["LangGraph 的 State/Node/Edge 分别是什么？", "checkpointer 解决什么问题？"])

h2("7. pytest 单元测试")
kv("是什么", "Python 测试框架：test_ 前缀函数、assert 断言、fixture 共享前置、parametrize 参数化、mock 替换外部依赖。")
kv("怎么用在你项目", "解析器（cURL/OpenAPI）→ 纯函数，直接断言；指纹去重 → 相同输入同指纹；归因规则 → 参数化覆盖 5 条规则；"
                "执行器 → mock httpx 返回固定响应。")
kv("面试会问", "你写过单测吗？覆盖哪些？")
kv("你怎么答", "目前有 4 个端到端/评测脚本；单测正在补，优先覆盖解析器、指纹、归因规则这三块纯逻辑，因为它们最容易回归。")
kv("30 分钟证据", "写 5 个测试：test_parse_curl、test_fingerprint_dedupe、test_triage_5xx、test_triage_401、test_read_only_filter。")
exercises(["fixture 的四种作用域？", "怎么 mock 一个 httpx 请求？", "覆盖率多少算够？"])

h2("8. CI / GitHub Actions")
kv("是什么", "提交代码自动跑 lint/test/build。最小流水线：checkout → setup-python → pip install → pytest。")
kv("面试会问", "你项目有 CI 吗？")
kv("你怎么答", "目前没有，跑测试靠手动执行 eval 脚本；加上 CI 只需要一个 yml，把 pytest 和 smoke 串起来，"
            "这也是我下一步要补的（面试可展示 yml 设计）。")
exercises(["一个最小 workflow 的四个步骤？", "怎么让 CI 只在 PR 时跑？"])

h2("9. 限流与幂等")
kv("限流", "固定窗口（INCR+EXPIRE）、滑动窗口（ZSet）、令牌桶（按速率补令牌）、漏桶。")
kv("幂等", "同一请求重复执行结果一致：幂等键（request_id）+ 唯一索引 / SETNX；写操作前查状态。")
kv("面试会问", "你怎么防重复提交？")
kv("你怎么答", "跑批用 run_id 唯一；缺陷按 run_item 唯一约束，重复生成不会建第二张单；如果加接口层，会用 request_id + Redis SETNX。")
exercises(["四种限流算法区别？", "幂等键应该放在哪一层？", "数据库唯一索引和 SETNX 各解决什么？"])

h2("10. 可观测性（日志 / 指标 / 追踪）")
kv("三件套", "日志（结构化、带 trace_id）、指标（QPS、P95、错误率）、追踪（一次请求的跨服务链路）。")
kv("你项目里已有的", "逐请求 trace（请求/响应/耗时/断言）、审计日志、/health 健康检查。")
kv("还缺的", "指标聚合（P95 统计）、trace_id 贯穿、Prometheus 暴露。")
kv("面试会问", "线上出问题你怎么定位？")
kv("你怎么答", "先看 /health 判断是应用还是 DB；再看单条用例 trace 复现请求；最后看审计日志确认谁在什么时候做了什么。"
            "指标化是我下一步要补的。")
exercises(["trace_id 怎么贯穿一次请求？", "P95 怎么算？为什么要看 P95 不看平均？"])

h2("11. 结构化输出与 Function Calling")
kv("结构化输出", "用 JSON Schema 约束模型输出（OpenAI 的 response_format / json_schema，或提示词 + 校验重试）。")
kv("Function Calling", "把工具名、描述、参数 schema 给模型，模型返回调用意图，外部执行后回灌结果。")
kv("面试会问", "怎么保证模型输出可解析？")
kv("你怎么答", "三层：schema 约束 + 解析容错（去 ```json 包裹）+ 业务校验（状态码范围、字段类型），非法就丢弃或重试一次。")
exercises(["strict 模式解决什么？", "工具描述为什么要写「何时不用」？"])

h2("12. SSE 与 WebSocket")
kv("SSE", "单向（服务端→客户端）、基于 HTTP、自动重连、文本流；浏览器 EventSource 不能自定义请求头。")
kv("WebSocket", "双向、需要握手升级、适合交互频繁场景（协作编辑、游戏）。")
kv("你怎么答", "我选 SSE：只需要服务端推进度，单向够用；又因为要带 Authorization，前端用 fetch 的 ReadableStream 读流，"
            "没用 EventSource。")
exercises(["SSE 怎么处理断线重连与补发？", "什么场景必须 WebSocket？"])

# ==================== 结尾 ====================
doc.add_paragraph()
para("—— 全部内容与项目代码、简历口径一致，可按 README 在本地一键运行后逐条验证。", 8.5,
     color=(0x59, 0x59, 0x59))

doc.save(OUT)
print("已生成:", OUT)
