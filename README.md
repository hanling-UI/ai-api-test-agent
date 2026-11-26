# AI 接口测试 Agent

> 给一个 OpenAPI 文档，自动生成测试用例、并发执行、失败归因，**人工确认后**提交缺陷。

不是又一个 RAG 问答：它真的发 HTTP 请求、真的跑测试、真的提单。

---

## 一、它解决什么

| 痛点 | 现状 | 这个项目 |
|---|---|---|
| 写用例慢 | 人工占测试工作量 40%+ | 6 维度自动生成（正常/边界/异常/鉴权/幂等/并发） |
| 边界容易漏 | 靠人想 | Schema 驱动 + 模型补全 |
| 失败要人判断是谁的错 | 逐个看日志 | 自动归因：**接口 bug / 用例错 / 环境问题** |
| 缺陷单写得烂 | 缺复现步骤 | 自动生成标题/步骤/curl |

## 二、六项能力对照

| 要求 | 本项目的实现 |
|---|---|
| 解决真实问题 | 用例编写与归因是测试的真实工时大头 |
| 完整后端工程 | Postgres 存储 + 并发执行器 + SSE + JWT 权限 + 审计 + Docker |
| 真 Agent 能力 | 解析 → 生成 → 执行 → **归因** → 提单；LangGraph 管决策流，含中断等人确认 |
| 上下文工程 | 生成时注入接口 schema；执行后压缩结果只送失败上下文给模型 |
| 可观测与评测 | 每条用例 trace；检出率 / 误报率 / 覆盖率 / P95 |
| 人机协同 | 用例可禁用；归因可复核；**提单前必须确认** |

## 三、架构

```
浏览器（原生 HTML/JS）
   │  fetch + SSE
   ▼
FastAPI ── JWT 鉴权 ── 项目级 RBAC（admin/tester/viewer）
   │
   ├── OpenAPI 解析 ──► endpoints 落库
   ├── 用例生成（LLM，6 维度，去重）
   │
   ▼
LangGraph 决策流
   execute（asyncio 并发 HTTP + 断言）
      ↓
   triage（规则优先 + LLM 解释）
      ↓
   draft（生成缺陷草稿）
      ↓
   [interrupt] 等待人工确认 ──► 提交缺陷
   │
   ▼
Postgres（用例/结果/缺陷/审计）+ 模型（qwen-flash / qwen-plus）
```

**为什么图只管决策**：批量执行是并发任务，放进节点会把状态搞乱；图负责「分支、循环、中断」。

## 四、快速开始

### 方式 A：Docker（推荐）

```bash
cp .env.example .env      # 填 OPENAI_API_KEY
docker compose up -d --build
```

打开 http://localhost:8000 ，用演示账号登录：

| 账号 | 密码 | 角色 |
|---|---|---|
| admin@demo.com | demo1234 | 管理员 |
| tester@demo.com | demo1234 | 测试（可生成/执行/提单） |
| viewer@demo.com | demo1234 | 只读（点执行会被 403） |

首次使用：

1. 左侧选中「示例商城 API」
2. 点「导入 OpenAPI」（会拉 mock 服务的 spec）
3. 点「生成用例」（约 1 分钟，45 条）
4. 「执行与报告」→ 运行全部用例
5. 「缺陷」→ 勾选草稿 → 确认提交

### 方式 B：本地

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
# 需要本地 Postgres（端口 5433）
uvicorn mock_server.main:app --port 9000 &
uvicorn main:app --port 8000
python -m app.seed --demo     # 建账号 + 导入 + 生成用例
```

## 五、演示脚本（60 秒）

```
① 登录 tester
② 运行全部用例 → 进度条实时推进（SSE）
③ 46 条：23 通过 / 23 失败
④ 失败里点开一条 → 看到请求、响应、断言 diff、curl
⑤ 归因列显示：bug / case_error
⑥ 缺陷页：3 条草稿（对应 mock 里埋的 3 个 bug）
⑦ 勾选 → 确认提交 → 状态变 submitted（写审计）
⑧ 用 viewer 登录 → 点运行 → 403
```

**mock 服务里埋的 3 个 bug**：

| # | 现象 | 期望 |
|---|---|---|
| 1 | `POST /users` 缺 `name` → 500 | 400 |
| 2 | `GET /orders/{id}` 不带 token → 200 | 401 |
| 3 | `GET /users?page=-1` → 500 | 400 |

## 六、评测

```bash
python eval/metrics.py        # 最近一次跑批
python eval/smoke.py          # 端到端（需先起 8000/9000）
```

指标定义：

| 指标 | 定义 |
|---|---|
| bug 检出率 | 检出的真 bug / 埋的 3 个 |
| 误报率 | 被判 bug 但实为用例问题 / 判 bug 总数 |
| 覆盖率 | 有用例的接口 / 总接口 |
| P95 延迟 | 单条用例执行耗时的 95 分位 |

## 七、技术选型与取舍

| 选择 | 理由 |
|---|---|
| LangGraph 只做决策流 | 中断恢复 + 提单确认 + 节点可观测；批量执行交给 asyncio |
| 规则优先的归因 | 5xx 优先判 bug、401↔200 判鉴权绕过；模型只写解释，避免判定漂移 |
| 400/422 视为等价 | 框架选哪个不代表接口有 bug，避免刷屏误报 |
| 人工基线用例 | 模型不保证命中已知缺陷，基线用例兜底（3 条） |
| 原生 HTML/JS | 无构建、部署简单，面试官 clone 就能跑 |

## 八、已知限制

- 被测服务是**内置 mock**（12 接口 + 3 bug）；换成真实 OpenAPI 只需改 `base_url` 并重新导入
- 归因基于规则 + 模型解释，复杂业务语义仍需人工复核（界面已提供）
- 图状态存在**进程内存**（InMemorySaver），重启后未确认的跑批需重跑；生产应换 Postgres checkpointer
- 未做：压测、契约测试、CI 集成（下一版）

## 九、目录

```
api-test-agent/
├── main.py              FastAPI 入口
├── app/
│   ├── api.py           路由（登录/项目/用例/跑批/缺陷/统计）
│   ├── graph.py         LangGraph 决策流
│   ├── models.py        表结构
│   ├── security.py      JWT + RBAC
│   ├── fixtures.py      基线用例
│   └── services/        解析/生成/执行/归因/缺陷
├── mock_server/         被测服务（12 接口 + 3 bug）
├── static/              前端（登录 + 单页应用）
├── eval/                smoke + metrics
└── docker-compose.yml
```
