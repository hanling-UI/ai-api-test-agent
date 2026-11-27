"""生成《八股文清单（项目版）》——沿用原文档结构，工程实践改成两个真实项目。"""
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = r"D:\项目\八股文清单（项目版）.docx"
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


def h1(t):
    p = doc.add_heading(t, level=1)
    for r in p.runs:
        _f(r, 13, True)


def h2(t):
    p = doc.add_heading(t, level=2)
    for r in p.runs:
        _f(r, 10.5, True)


def para(t, size=9, bold=False, color=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.05
    _f(p.add_run(t), size, bold, color)


def q_line(i, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(2)
    pf.space_after = Pt(0)
    pf.line_spacing = 1.05
    _f(p.add_run(f"★{i}. {text}"), 9, True)


def ans(label, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(0)
    pf.line_spacing = 1.05
    pf.left_indent = Cm(0.3)
    _f(p.add_run(f"· {label}："), 9, True)
    _f(p.add_run(text), 9)


# 数据：{章: [(题, 定义, 原理, 实践)]}
DATA = {}

DATA["第 1 章　计算机网络（10 题）"] = [
    ("OSI 七层和 TCP/IP 四层模型分别是什么？",
     "OSI 自下而上：物理、数据链路、网络、传输、会话、表示、应用；TCP/IP 四层：网络接口、网际、传输、应用。",
     "分层是为了解耦，每层只对相邻层负责；TCP/IP 把高三层合并为应用层，因为会话与表示实际由应用自己处理。",
     "没在项目里直接落地。可类比我给 Agent 分的层（接入 / 生成 / 执行 / 归因 / 治理），每层只对上负责，改一层不牵动其他层。"),
    ("TCP 三次握手的过程和原因？",
     "客户端 SYN → 服务端 SYN+ACK → 客户端 ACK。",
     "三次是为了双向确认收发能力，并同步初始序列号（ISN），避免历史连接的旧报文被当成新连接。",
     "项目二的进度推送用 SSE（长连接），网关默认读超时会掐断推流，所以要把 keep-alive 和读超时调大。"),
    ("TCP 四次挥手的原因和 TIME_WAIT 的作用？",
     "主动方 FIN → 对方 ACK；对方数据发完再 FIN → 主动方 ACK。TIME_WAIT 等 2MSL。",
     "TCP 全双工，两个方向要独立关闭，所以比握手多一次；等 2MSL 是为了保证最后 ACK 能到达，并让旧报文在网络中消亡。",
     "本地反复重启 uvicorn 会报 Errno 10048 端口被占用，本质就是 TIME_WAIT；我写了 stop.ps1 释放端口再启动。"),
    ("TCP 和 UDP 的核心区别及适用场景？",
     "TCP 面向连接、可靠、有序；UDP 无连接、不可靠、开销小。",
     "TCP 靠序列号、ACK、重传与拥塞控制换可靠性；UDP 牺牲可靠性换低延迟。",
     "项目二的执行进度必须有序到达，所以用基于 TCP 的 SSE；如果做实时语音，丢帧无感知，会用 UDP。"),
    ("HTTP 和 HTTPS 的区别及加密过程？",
     "HTTPS = HTTP + TLS，默认 443。",
     "非对称加密安全交换一个对称密钥，后续通信走对称加密；客户端还要验证证书链是否可信。",
     "线上部署在 Render，默认 HTTPS；本地 127.0.0.1 被浏览器视为安全上下文，所以 getUserMedia 能调摄像头。"),
    ("常见的 HTTP 状态码有哪些？",
     "2xx 成功、3xx 重定向、4xx 客户端错误、5xx 服务端错误。",
     "语义分层：4xx 表示请求方的问题，5xx 表示服务端没处理好。",
     "项目二的归因规则完全建立在这上面：5xx 判接口缺陷、401/403 判环境问题、4xx 与期望不一致判用例问题。"),
    ("GET 和 POST 的区别？",
     "GET 取资源、参数在 URL、幂等可缓存；POST 提交数据、参数在 Body、非幂等。",
     "本质区别是语义与幂等性；传输安全靠 HTTPS，不是靠换方法。",
     "生成用例默认只覆盖 GET/HEAD（只读模式），就是因为 POST 可能写数据或计费，这正是 GET 幂等语义的应用。"),
    ("Cookie 和 Session 的区别？",
     "Cookie 存客户端；Session 存服务端，靠 SessionID 关联。",
     "HTTP 无状态，需要额外机制保持状态；Cookie 是载体，Session 是服务端存储。",
     "项目一的访问口令用 Cookie（gptr_access 存 SHA-256 令牌）；项目二把它存成项目的 custom_headers 复用，"
     "自己则用无状态 JWT，避免多实例部署时掉线。"),
    ("在浏览器输入 URL 到页面展示的过程？",
     "URL 解析 → DNS → TCP/TLS 建连 → 发 HTTP 请求 → 服务端处理 → 浏览器渲染。",
     "首屏时间由 TTFB 与资源加载决定；长任务会拉长 TTFB。",
     "项目一报告生成慢，用 SSE 把首字延迟压到 1 秒内；排查时看 Network 面板的 TTFB 判断是服务端慢还是资源慢。"),
    ("DNS 解析过程及 ARP 的作用？",
     "DNS 把域名换成 IP，先查本机缓存/hosts，再向本地 DNS 逐级问根/顶级/权威；ARP 在局域网内把 IP 解析成 MAC。",
     "IP 是逻辑地址跨网段不变，MAC 是物理地址逐跳重写。",
     "没落地。本地开发直接用 127.0.0.1 绕过 DNS；线上域名解析由平台托管。"),
]

DATA["第 2 章　操作系统（8 题）"] = [
    ("进程和线程的区别？",
     "进程是资源分配的最小单位，线程是 CPU 调度的最小单位；进程独立内存，线程共享。",
     "切换进程要换页表，开销大；线程切换只换栈与寄存器。",
     "项目二用 FastAPI + asyncio 扛 I/O（等模型、等 HTTP），因为瓶颈在等待；如果做批量 CPU 解析，会用多进程绕开 GIL。"),
    ("进程的状态及转换？",
     "就绪、运行、阻塞（还有新建与终止）。",
     "缺 CPU 变就绪，缺事件（I/O）变阻塞；阻塞的事件完成后只能回到就绪，不能直接进运行。",
     "没直接落地，但可作为解释：跑批任务卡在等 HTTP 响应时属于阻塞态，所以并发数要设上限（Semaphore 5）。"),
    ("死锁的四个必要条件及预防？",
     "互斥、请求并保持、不可剥夺、循环等待；破坏任一即可预防，最常用按固定顺序申请资源。",
     "死锁是资源竞争 + 持有等待形成的环；顺序申请破坏环。",
     "项目二所有外部调用都设超时（10s），就是防止某类资源被无限占用；批量任务单条失败不影响整体，避免互相等待。"),
    ("虚拟内存的作用及页面置换算法？",
     "让每个进程以为自己独占连续内存，靠分页与置换（LRU 淘汰最久未使用）。",
     "解决内存隔离与容量限制，利用局部性原理。",
     "可类比我做向量规模估算：30 万块 × 1024 维 × 4B ≈ 1.2GB，加 HNSW 图结构会顶到内存上限，所以要 halfvec 或分区。"),
    ("用户态和内核态的区别及切换？",
     "用户态无特权、不能直接访问硬件；内核态有最高权限。切换靠系统调用、异常、硬件中断。",
     "切换有开销，所以批量操作比逐次调用快。",
     "写日志时不要一条一条 write，改成批量或带缓冲，这是我在执行器里把 trace 一次性落库的原因。"),
    ("进程间通信（IPC）方式有哪些？",
     "管道、消息队列、共享内存、信号量、Socket。",
     "共享内存最快但不拷贝需配信号量同步；Socket 能跨机器。",
     "项目二容器里跑两个进程（被测 mock 与应用），它们通过 Socket（HTTP）通信；Docker 网络就是跨容器 Socket。"),
    ("线程同步方式和互斥锁 vs 信号量？",
     "互斥锁保证只有一个线程进临界区（有所有权）；信号量是计数器，控制最多 N 个并发。",
     "互斥锁是 0/1，信号量可大于 1；底层靠 CAS 原子指令与 futex。",
     "项目二的 asyncio.Semaphore(5) 就是信号量语义：最多 5 个请求同时在飞，避免把被测服务打挂。"),
    ("常见的 IO 模型有哪些？",
     "阻塞（BIO）、非阻塞（NIO）、IO 多路复用（epoll）、异步 IO。",
     "多路复用用一个线程管多个连接，避免为每个连接开线程。",
     "uvicorn 底层就是 epoll；所以在异步代码里不能用 requests（阻塞），必须用 httpx.AsyncClient。"),
]

DATA["第 3 章　计算机组成原理（3 题）"] = [
    ("为什么用补码表示负数？",
     "把减法变成加法，符号位可以直接参与运算。",
     "计算机只有加法器，补码省掉减法电路；0 也只有一种表示。",
     "没落地，答原理即可。"),
    ("Cache 和内存的区别？",
     "Cache 快且小，内存慢且大，靠局部性原理缓解 CPU 与内存速度差。",
     "多级缓存（L1/L2/L3）逐级放大容量、降低延迟。",
     "可类比我做的缓存思路：检索结果落 Redis（下一步），本质就是用一层更快的小容量存储换延迟。"),
    ("32 位和 64 位的本质区别？",
     "寄存器与虚拟地址位宽不同；32 位寻址上限 4GB，64 位大得多，通用寄存器也更多。",
     "位宽决定单次能处理的地址范围与数据宽度。",
     "线上 Render 免费实例是 512MB 内存，属于硬约束，所以我控制并发与批量大小。"),
]

DATA["第 4 章　数据库 MySQL（9 题）"] = [
    ("事务的 ACID 特性及底层实现？",
     "原子性、一致性、隔离性、持久性。",
     "原子性靠 undo log（回滚），持久性靠 redo log（防掉电），隔离性靠锁 + MVCC，一致性是最终目标。",
     "我的项目实际用 PostgreSQL，原理一致（WAL 对应 redo，MVCC 实现相同）；跑批结果与缺陷写入放在一个事务里，避免半写状态。"),
    ("事务的隔离级别及解决的问题？",
     "读未提交（脏读）、读已提交（解决脏读）、可重复读（解决不可重复读）、串行化（解决幻读）。",
     "级别越高一致性越强、并发越低。",
     "没做过隔离级别调优；可答 PG 默认读已提交，MySQL 默认可重复读。"),
    ("MySQL 默认隔离级别及如何解决幻读？",
     "默认 RR；快照读用 MVCC，当前读用 Next-Key Lock（间隙锁）。",
     "MVCC 靠 ReadView 读历史版本，实现读写不冲突。",
     "没落地，答原理；补一句我用 PG，PG 用 SSI 处理可串行化。"),
    ("聚簇索引和非聚簇索引？",
     "聚簇索引叶子存整行数据（通常是主键）；非聚簇索引叶子存主键值。",
     "按主键查一次即得整行；按二级索引查要先拿主键再回表。",
     "项目二主键用自增 bigserial，避免随机 UUID 造成 B+ 树页分裂；PG 的堆表结构与 MySQL 聚簇索引不同，这点要能说清。"),
    ("回表和覆盖索引？",
     "二级索引查到主键后再回主键树取整行叫回表；要查的列全在索引里则免回表，叫覆盖索引。",
     "回表是一次额外随机 IO，覆盖索引能省掉。",
     "项目二列表接口只查必要字段（不 SELECT *），就是为了尽量走覆盖索引。"),
    ("索引失效的常见场景？",
     "最左前缀不满足、列上做函数或运算、隐式类型转换、LIKE '%xx'、OR 两侧未都建索引。",
     "索引是有序结构，一旦对列做运算就无法按序定位。",
     "项目二对参数做强类型校验，避免字符串传数字造成隐式转换；上线前用 EXPLAIN 看有没有全表扫。"),
    ("EXPLAIN 的 type 字段常见值？",
     "由差到好：ALL、index、range、ref、eq_ref、const。",
     "type 反映访问方式，ALL 是全表扫。",
     "我上线前会看 type 是否为 ALL、Extra 里有没有 Using filesort / Using temporary。"),
    ("慢查询如何排查？",
     "开慢查询日志 → 定位慢 SQL → EXPLAIN → 加索引 / 改 SQL / 分页。",
     "先定位再优化，避免盲目加索引。",
     "PG 里对应 pg_stat_statements；项目二统计接口如果变慢，会先看是否缺索引。"),
    ("分库分表适用场景？",
     "单表超千万或单库读写/磁盘到瓶颈时做水平或垂直拆分。",
     "是最后手段，优先索引、归档、读写分离、缓存。",
     "没落地。我的量级（几千条用例）不需要；如果跑批记录涨到千万，会先按项目分区。"),
]

DATA["第 5 章　Linux（8 题）"] = [
    ("用 grep 查找特定字符串？",
     "grep 按行匹配，常用 -r 递归、-n 行号、-C 上下文、-c 计数。",
     "正则匹配文本行。",
     "排查 401 时用 grep -rn 'ERROR' 日志目录，配合 -C 5 看上下文。"),
    ("用 find 按文件名查找？",
     "find 按属性递归查找，如 -name、-mtime、-size。",
     "遍历目录树按条件筛选。",
     "清理日志：find /var/log -name '*.log' -mtime +7 -size +100M，先 -print 确认再删。"),
    ("管道的概念？",
     "| 把前一个命令的 stdout 作为后一个命令的 stdin。",
     "进程间通过管道传递字节流，无需临时文件。",
     "统计失败接口：cat access.log | grep 500 | awk '{print $7}' | sort | uniq -c | sort -nr。"),
    ("查看系统进程状态？",
     "ps aux 看快照，top 看实时资源。",
     "load average 高但 CPU 空闲，说明大量进程卡在不可中断 IO。",
     "排查服务卡死时先看 top 的 load 与 D 状态进程。"),
    ("查看端口占用？",
     "ss -tuln 或 netstat -tuln；Windows 用 netstat -ano。",
     "列出监听端口与对应进程。",
     "本地 8000 / 9000 被占会报 Errno 10048，我就是靠查端口找到残留进程，并写了 stop.ps1。"),
    ("chmod 755/644 和 chown 的作用？",
     "755 属主读写执行、其他人读执行；644 属主读写、其他人只读；chown 改属主与属组。",
     "权限位分属主/属组/其他人三组。",
     "部署脚本给 755；含密钥的 .env 必须 600 或 644，绝不用 777。"),
    ("软链接和硬链接的区别？",
     "软链接是快捷方式（指向路径）；硬链接是同一 inode 的多个名字。",
     "删源文件软链失效，硬链仍可访问；硬链不能跨文件系统。",
     "版本发布可用软链做秒级切换与回滚（本项目未落地）。"),
    ("查看磁盘和内存使用情况？",
     "df -h 看磁盘，free -m 看内存，重点看 available。",
     "available 才是可用内存，used 高低不代表有问题。",
     "Render 免费实例 512MB，跑批量任务时要控并发，否则容易 OOM。"),
]

DATA["第 6 章　Python 与大模型基础（9 题）"] = [
    ("列表和元组的区别？",
     "列表可变（动态数组），元组不可变（可哈希、省内存）。",
     "不可变意味着可做 dict 的 key、可安全共享。",
     "用例指纹用元组/字符串做 key，避免可变对象当 key。"),
    ("深拷贝和浅拷贝的区别？",
     "浅拷贝只复制外层，内层仍是引用；深拷贝递归复制所有层。",
     "嵌套可变对象共享会导致互相污染。",
     "组装 run_items 时避免复用同一个 dict 对象，否则多条结果会互相覆盖。"),
    ("装饰器的作用？",
     "接收函数返回新函数，不修改原代码添加功能。",
     "本质是闭包 + 高阶函数；异步要写 async 包装器并 await。",
     "FastAPI 的 Depends(require_role) 就是依赖注入式装饰，统一做权限校验。"),
    ("生成器（Generator）？",
     "用 yield 惰性求值，每次产出一个值。",
     "节省内存，适合流式与大数据遍历。",
     "SSE 的底层就是生成器：StreamingResponse 一边收一边推，实现进度条效果。"),
    ("Token 和上下文窗口？",
     "Token 是模型处理的最小单位；上下文窗口是一次请求能带的最大 token 数（输入 + 输出）。",
     "超窗口会被截断或报错，成本按 token 计。",
     "生成用例前把接口 schema 压成摘要，失败归因只喂失败上下文，都是在控 token 预算。"),
    ("Temperature 和 Top-p 的作用？",
     "Temperature 调概率分布平滑度（越低越确定）；Top-p 是核采样，只保留累积概率达 p 的候选。",
     "两者都影响随机性，一般只调一个。",
     "生成用例用 0.2 保证稳定；评测时必须 0，否则两次结果不可比。"),
    ("Zero-shot 和 Few-shot？",
     "不给示例直接问是零样本；给几个输入输出示例是少样本。",
     "示例能显著提升格式遵循度，但格式错会带偏。",
     "生成用例的 prompt 里给了输出 JSON 的格式示例，属于 few-shot。"),
    ("什么是 CoT（思维链）？",
     "让模型先输出推理步骤再给结论。",
     "把复杂推理拆成中间步骤，降低一步到位的难度。",
     "归因解释用短推理；分类这种简单任务不加，纯浪费 token。"),
    ("如何解决大模型幻觉？",
     "模型生成看似合理但无依据的内容。",
     "根因是它在做概率续写，不是在查证。",
     "项目二的做法：不让模型判定对错，只让它写解释；判定交给规则，从源头绕开幻觉。"),
]

DATA["第 7 章　RAG 与 Agent（11 题）"] = [
    ("简述 RAG 的完整流程？",
     "加载 → 切分 → 向量化 → 入库 → 检索 → 重排 → 拼 Prompt 生成。",
     "本质是把大搜索空间缩小到几段内容，让模型在证据内作答。",
     "项目一全链路都做过；收益最大的两步是加 BM25 混合检索与重排，换更大生成模型反而提升最小。"),
    ("文档切分策略及大小权衡？",
     "固定长度、按标点、按语义；切太大混主题，切太小丢上下文。",
     "要匹配文档平均长度与检索粒度。",
     "我最初 500 字切分，20 篇文档每篇约 355 字，结果一篇一块、检索失效；改 200/40 后切成 43 块，Top1 相似度从 0.51 升到 0.57。"),
    ("混合检索和 RRF 融合？",
     "BM25（关键词精确匹配）+ 向量（语义匹配），用 RRF 按名次合并。",
     "两路互补：编号、专有名词靠 BM25，改写、同义靠向量。",
     "项目一：纯向量 0.742，加 BM25 混合后 0.755。"),
    ("RRF 公式及其优点？",
     "score = Σ 1/(k + rank)，k 常取 60。",
     "两路分数量纲不可比，RRF 只看排名，天然免疫量纲差异、零训练成本。",
     "手写的 RRF，k=60；调大对排名差异更不敏感。"),
    ("Rerank 重排及其与向量检索的区别？",
     "用交叉编码器对「查询-文档」逐对精排。",
     "向量是双塔（快但粗），交叉编码器是逐对打分（准但慢），所以只对 Top N 候选做。",
     "项目一加了一层重排：0.755 → 0.764，代价 +260ms P95；我如实写了「性价比一般」。"),
    ("如何评估 RAG 系统？",
     "看召回率、精度、忠实度；常用 RAGAS 一类框架，或自建标注集。",
     "先召回后精度：召回不到，后面全白搭。",
     "我自建 5 条查询做抽样评测，统计语义覆盖 0.712 → 0.764，同时记录上下文压缩 93%（25492 → 1703 字符）；样本小，所以更强调压缩率这个硬指标。"),
    ("Agent 和普通 LLM 的区别？",
     "Agent 有工具、记忆与循环控制，能拆解目标并迭代。",
     "LLM 是一次生成；Agent 是多步「决策-执行-观察」。",
     "项目二用状态图编排「执行 → 归因 → 确认 → 提交」，有工具、有循环、有中断，属于任务型 Agent。"),
    ("Function Calling 原理？",
     "把工具名、描述、参数（JSON Schema）给模型，模型输出调用意图，外部执行后把结果回灌。",
     "模型只负责选工具与填参数，不负责执行。",
     "项目二没直接用官方 FC API，而是用 LangGraph 节点显式调度工具（解析、执行、断言），本质相同、可控性更强。"),
    ("什么是 ReAct 框架？",
     "Thought → Action → Observation 循环。",
     "让模型边推理边行动，用观察修正下一步。",
     "我没用自由 ReAct（容易跑飞），改用固定状态图；面试要如实说这一点。"),
    ("Agent 工具调用失败怎么处理？",
     "错误作为 Observation 回灌模型，配合重试、修正参数、降级。",
     "失败信息要结构化，模型才能修正。",
     "项目二：单请求超时 10s + 重试；单条失败记 env 不影响整批；模型只写解释，不参与重试决策。"),
    ("什么是 MCP？和 Function Calling 的区别？",
     "MCP 是工具/数据接入的统一协议（类似 USB-C）；FC 是模型侧「决定调哪个函数」的能力。",
     "FC 解决「模型怎么选」，MCP 解决「工具怎么被标准化接入」。",
     "未落地。我的工具层已经是统一接口 + 描述，要包成 MCP Server 主要是加协议层——面试就这么说。"),
]

DATA["第 8 章　你项目相关、原清单没有的 12 题"] = [
    ("LangGraph 的 State / Node / Edge / checkpointer 分别是什么？",
     "State 是共享状态（TypedDict）；Node 是处理函数；Edge 决定下一步；checkpointer 持久化状态。",
     "图执行 = 按边推进节点，每步读写 state；checkpointer 以 thread_id 存快照。",
     "项目二：State 存 run_id 与统计，四个节点 execute/triage/draft/confirm，interrupt_before=['confirm']，thread_id=run-{id}。"),
    ("interrupt（中断）怎么实现与恢复？",
     "编译时 interrupt_before 指定节点，跑到该节点前暂停；恢复时用同一 thread_id 再 invoke(None)。",
     "暂停点由 checkpointer 保存，恢复即从快照继续。",
     "项目二在生成缺陷草稿后暂停，等人在界面点确认，再 resume 把状态置为 done。"),
    ("SSE 和 WebSocket 怎么选？EventSource 有什么限制？",
     "SSE 单向、基于 HTTP、自动重连；WebSocket 双向、需升级握手。",
     "SSE 适合服务端推流，WebSocket 适合高频双向交互。",
     "项目二用 SSE 推进度；因为要带 Authorization 头，前端用 fetch 的 ReadableStream 读流，没用 EventSource（它不能自定义头）。"),
    ("幂等怎么设计？",
     "同一请求重复执行结果一致：幂等键 + 唯一索引/SETNX，或先查状态再执行。",
     "关键是找到业务唯一标识（run_id、request_id）。",
     "项目二：用例指纹去重、缺陷按 run_item 唯一、导入覆盖式重建；接口层再加 request_id 就完整了。"),
    ("常见限流算法有哪几种？",
     "固定窗口、滑动窗口、令牌桶、漏桶。",
     "固定窗口有临界突刺；令牌桶允许突发；漏桶平滑输出。",
     "项目二目前靠 Semaphore 控并发；下一步用 Redis INCR + EXPIRE 做「每项目每天 N 次」的固定窗口限流。"),
    ("Redis 在你项目里能解决什么？",
     "KV + 五大数据结构；缓存、锁、限流、排行榜。",
     "旁路缓存 Cache-Aside；分布式锁用 SET NX PX + Lua 释放。",
     "未落地，但能说清三处用途：跑批限流、统计缓存（ZSet 算 P95）、幂等去重（SETNX）。"),
    ("结构化输出怎么做才可靠？",
     "JSON Schema 约束 + 解析容错 + 业务校验。",
     "模型可能加解释或代码块包裹，必须容错解析。",
     "项目二三层：schema 约束输出 → 去掉 ```json 包裹 → 校验状态码范围与字段类型，非法直接丢弃。"),
    ("pytest 的 fixture 与 paramtrize 怎么用？",
     "fixture 提供测试前置（作用域 function/class/module/session）；parametrize 参数化多组输入。",
     "fixture 用依赖注入方式复用准备逻辑，避免重复代码。",
     "正在补单测：解析器与归因规则用 parametrize 覆盖多组输入，DB 用 session 级 fixture。"),
    ("一个最小 CI 流水线包含什么？",
     "checkout → 装依赖 → 跑测试 → （可选）构建镜像。",
     "每次提交自动验证，防止回归。",
     "目前没有 CI，跑 eval 脚本靠手动；下一步加 GitHub Actions：pytest + smoke。"),
    ("可观测性三件套是什么？",
     "日志（结构化、带 trace_id）、指标（QPS/P95/错误率）、追踪（一次请求的链路）。",
     "三者互补：日志看细节，指标看趋势，追踪看链路。",
     "项目二已有逐请求 trace、审计日志、/health；缺指标聚合，这是下一步。"),
    ("OpenAPI 的 security 继承规则是什么？",
     "操作级写了 security 就覆盖全局；写空数组 [] 表示公开；完全没写才继承全局声明。",
     "这是规范里的覆盖语义，容易实现错。",
     "我一开始一律按全局判，导致 Petstore 上公开接口被误判为需鉴权、产生 8 条假 bug；修正后 19 接口变成需鉴权 9 / 公开 10。"),
    ("为什么 400 和 422 可以视为等价？",
     "都表示参数不合法，只是框架选择的默认码不同（FastAPI 用 422，很多服务用 400）。",
     "语义相同，强行区分会产生大量误报。",
     "项目二断言里把 {400,422} 视为等价，改完后噪声明显下降。"),
]


# ==================== 封面 ====================
t = doc.add_heading("八股文清单（项目版 · 背诵用）", level=0)
for r in t.runs:
    _f(r, 18, True)
para("结构：第一部分问题总览（70 题）→ 第二部分逐题分层作答（定义 / 原理 / 结合你的项目）。", 8.5,
     color=(0x59, 0x59, 0x59))
para("标★为高频必考。工程实践一栏已按你的真实项目改写；没落地的写「未落地」并给出可说的迁移思路。", 8.5,
     color=(0x59, 0x59, 0x59))
doc.add_paragraph()

# ==================== 第一部分 ====================
h1("第一部分　问题总览（70 题）")
para("先只看题目自测：能口述出「定义 + 原理 + 我项目里怎么用」三句，才算过。", 8.5, color=(0x59, 0x59, 0x59))
n = 1
for chapter, items in DATA.items():
    h2(chapter)
    for i, (q, *_rest) in enumerate(items, 1):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_after = Pt(0)
        pf.line_spacing = 1.05
        pf.left_indent = Cm(0.35)
        _f(p.add_run(f"{chapter.split('（')[0].replace('第 ', '').replace(' 章　', '.')}{i}  {q}"), 9)

# ==================== 第二部分 ====================
doc.add_page_break()
h1("第二部分　逐题作答（定义 · 原理 · 结合你的项目）")
for chapter, items in DATA.items():
    h2(chapter)
    for i, (q, definition, principle, practice) in enumerate(items, 1):
        q_line(i, q)
        ans("一句话定义", definition)
        ans("底层原理", principle)
        ans("工程实践", practice)

doc.add_paragraph()
para("—— 背诵方法：先看第一部分题目自测，卡住的再翻第二部分；每章过完合上文档口述一遍。", 8.5,
     color=(0x59, 0x59, 0x59))

doc.save(OUT)
print("已生成:", OUT)
