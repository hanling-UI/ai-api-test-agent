# AI 接口测试 Agent

> 给一个接口服务（OpenAPI / Postman / cURL 任选），自动生成测试用例、并发执行、失败归因，**人工确认后**提交缺陷。

不是聊天机器人，也不是"套了 prompt 的页面"：它真的发 HTTP 请求、真的跑断言、真的提单。

- **在线体验**：https://ai-api-test-agent.onrender.com
- **演示账号**：`admin@demo.com` / `tester@demo.com` / `viewer@demo.com`，密码均为 `demo1234`
- 免费实例 15 分钟无访问会休眠，首次打开约需 30~60 秒

---

## 一、解决什么问题

| 痛点 | 现状 | 这个项目 |
|---|---|---|
| 写用例慢 | 人工编写占测试工时 40%+ | 按 6 个维度自动生成：正常 / 边界 / 异常 / 鉴权 / 幂等 / 并发 |
| 边界容易漏 | 靠人想 | Schema 驱动 + 模型补全 |
| 失败要人判断是谁的错 | 逐条翻日志 | 自动归因：**接口 bug / 用例错误 / 环境问题** |
| 缺陷单写得烂 | 缺复现步骤 | 自动生成标题 / 步骤 / 期望 / 实际 / 复现 curl |
| 写操作风险 | 自动化误触发计费或写接口 | 默认只覆盖只读接口，需显式放开 |

---

## 二、核心流程

```
接入：OpenAPI / Postman 集合 / 粘贴 cURL / 需要口令的服务
   ↓
生成：结构化输出（JSON Schema 约束）+ 指纹去重
   ↓
执行：asyncio 并发 + 超时 + 断言（状态码 / 字段 / 耗时），逐条记录 trace
   ↓
归因：规则优先（5xx→bug、401↔200→鉴权绕过、4xx→用例问题）+ 模型补解释
   ↓
提单：生成缺陷草稿 →【人工确认】→ 提交 + 审计留痕
```

---

## 三、架构

```
浏览器（原生 HTML/CSS/JS，无构建）
   │  fetch + SSE
   ▼
FastAPI ── JWT 鉴权 ── 项目级 RBAC（系统管理员 / 项目 admin / tester / viewer）
   │
   ├── 解析层：OpenAPI 解析 / Postman 集合 / cURL 解析 / 文档路径自动探测
   ├── 生成层：6 维度用例生成 + Schema 校验 + 指纹去重
   ├── 执行层：asyncio + Semaphore 并发、超时、跟随重定向、断言引擎
   ├── 归因层：规则引擎 + LLM 解释（判定不交给模型，避免漂移）
   ├── 确认层：LangGraph 状态图（execute → triage → draft →【interrupt】→ confirm）
   └── 治理层：审计日志、成员管理、只读模式、统计
   ▼
PostgreSQL（用例 / 跑批 / 缺陷 / 审计 / 账号）+ 大模型（qwen-flash / qwen-plus）
```

**为什么图只管决策**：批量执行是并发任务，塞进图里状态会爆炸；图负责「分支、循环、中断等人确认」。

---

## 四、评测结果（真实跑出来的）

| 被测对象 | 用例数 | 通过 | 失败 | 检出 bug | 误报 | 结论 |
|---|---|---|---|---|---|---|
| 内置示例商城（预埋 3 个缺陷） | 46 | 23 | 23 | **3/3** | 0 | 3 个 bug 全部命中 |
| gpt-researcher（本人真实项目，22 接口） | 41 | 11 | 30 | 0 | 0 | 无服务端缺陷；失败均为 404（用例使用虚构 ID） |

**两组对比的意义**：既能发现真问题，也能明确说"这里没问题"，并把噪声（测试数据缺失）与缺陷分开——只会喊 bug 的工具不可信。

复现方式：

```bash
python eval/smoke.py     # 端到端：登录→跑批→归因→提单→越权校验
python eval/metrics.py   # 检出率 / 误报率 / 覆盖率
python eval/roles.py     # 三种角色的权限边界
```

---

## 五、快速开始

### 方式 A：Docker（推荐）

```bash
cp .env.example .env          # 填 OPENAI_API_KEY
docker compose up -d --build  # db + 被测 mock + 应用
```

打开 http://localhost:8000 ，用 `admin@demo.com / demo1234` 登录。

### 方式 B：本地

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn mock_server.main:app --port 9000 &   # 被测服务
uvicorn main:app --port 8000                 # 应用
python -m app.seed --demo                    # 建账号 + 导入 + 生成用例
```

### 方式 C：云上部署（Render + Neon）

1. 推送到 GitHub → Render 新建 Web Service（Runtime 选 **Docker**，Plan 选 **Free**）
2. 环境变量：

```
DATABASE_URL     postgresql+psycopg://user:pass@host/db?sslmode=require
OPENAI_API_KEY   百炼 key
OPENAI_BASE_URL  https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_FAST         qwen-flash
LLM_SMART        qwen-plus
JWT_SECRET       随机长串
DEMO_PASSWORD    demo1234
```

3. `start.py` 会在容器内同时拉起被测 mock（127.0.0.1:9000）与应用（$PORT），
   首次启动自动建账号、示例项目、接口与基线用例（幂等，不消耗模型额度）。

---

## 六、三种接入方式

| 服务类型 | 做法 | 备注 |
|---|---|---|
| 标准 OpenAPI | 填服务根地址 → 从服务地址导入（自动探测 `openapi.json`/`v3/api-docs`/`swagger.json`/`apispec_1.json` 等） | 最常用 |
| 无文档 / 文档被登录拦住 | 上传 spec 文件（JSON/YAML） | — |
| 手上只有一条请求 | 粘贴 cURL，或上传 Postman 集合 | 生成接口 + 立即可跑的基线用例 |
| 服务需要口令 / Cookie | 「服务有口令？」自动登录拿 Cookie，或手工设置请求头 | 覆盖 Cookie / API-Key |

导入时自动排除 `/login`、`/logout`、`/static`、`/docs`、`/openapi.json` 等**非业务接口**，避免噪声用例。

---

## 七、设计取舍

| 决策 | 理由 |
|---|---|
| 归因**规则优先**、模型只写解释 | 判定必须稳定可复现；5xx、401↔200 这类信号不应交给概率模型 |
| 400 / 422 视为等价 | 都属于"参数不合法"，框架选哪个不代表接口有缺陷 |
| 生成默认只覆盖只读接口 | 避免自动化误触发计费或写操作；需要时显式关闭 |
| 人工基线用例 + 模型生成 | 模型不保证命中已知缺陷，基线用例兜底（3 条） |
| LangGraph 只管决策流 | 中断恢复 + 提单确认 + 节点可观测；批量执行交给 asyncio |
| 前端原生 JS 无构建 | 部署简单，clone 即跑 |

---

## 八、权限模型

| 角色 | 能力 |
|---|---|
| 系统管理员 | 建项目、看全部项目、管理成员、查看审计 |
| 项目 admin | 项目内全部操作 + 成员管理 |
| tester | 导入 / 生成 / 执行 / 提单，不能管成员 |
| viewer | 只读，写操作按钮隐藏，接口层返回 403 |

前端隐藏 + 后端 `require_role` 双保险，绕过前端直接调 API 同样会被拦。

---

## 九、已知限制

- 用例之间**没有数据传递**：`/api/reports/{id}` 这类用例使用虚构 ID，会产生 404 噪声。下一版做 JSONPath 变量提取（先查列表取真实 id 再测详情）。
- 图状态存在进程内存（InMemorySaver），容器重启后未确认的跑批需重跑；生产应换 Postgres checkpointer。
- 未覆盖：UI 自动化、性能压测、契约测试、CI 定时调度。
- 演示账号密码写在环境变量里，生产应接入企业 SSO / OIDC。

---

## 十、目录

```
api-test-agent/
├── main.py                  FastAPI 入口（HTML 注入 build 号、静态资源禁缓存）
├── start.py                 容器入口：内部拉起 mock + 应用
├── app/
│   ├── api.py               路由（登录/项目/用例/跑批/缺陷/统计/成员/审计/个人中心）
│   ├── graph.py             LangGraph 决策流（含 interrupt 人工确认）
│   ├── bootstrap.py         首启自举（账号/示例项目/接口/基线用例）
│   ├── security.py          JWT + RBAC
│   ├── models.py            表结构
│   ├── fixtures.py          人工基线用例
│   └── services/            parser / curlparse / generator / executor / triage / issues / llm
├── mock_server/             被测服务（12 接口 + 3 个预埋缺陷）
├── static/                  前端（登录页 + 单页应用）
├── eval/                    smoke / metrics / roles / curl_import / new_project
└── docker-compose.yml
```
