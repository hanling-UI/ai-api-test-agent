"""应用入口。"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.config import STATIC_DIR
from app.db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="AI API Test Agent", version="1.0.0")
app.include_router(router)
app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")


def build_id() -> str:
    """静态文件最新修改时间，用作版本号。文件一改，版本号就变。"""
    try:
        return str(int(max(f.stat().st_mtime for f in STATIC_DIR.glob("*"))))
    except ValueError:
        return "1"


def render_page(name: str) -> HTMLResponse:
    """读 HTML，把 __BUILD__ 换成当前版本号，并要求浏览器清掉本站缓存。"""
    html = (STATIC_DIR / name).read_text(encoding="utf-8").replace("__BUILD__", build_id())
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            # 只清 HTTP 缓存，不动 localStorage 里的登录状态
            "Clear-Site-Data": '"cache"',
        },
    )


@app.on_event("startup")
def _startup() -> None:
    from app.bootstrap import bootstrap

    init_db()
    bootstrap()          # 首次启动自动建账号/示例项目/接口/基线用例（幂等）


@app.middleware("http")
async def no_cache_assets(request: Request, call_next):
    """静态资源也不缓存，避免改了 JS 浏览器还在用旧的。"""
    response = await call_next(request)
    if request.url.path.startswith("/assets/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


@app.get("/", include_in_schema=False)
def index():
    return render_page("index.html")


@app.get("/login", include_in_schema=False)
def login_page():
    return render_page("login.html")


@app.get("/health")
def health():
    """带上数据库状态，出问题一眼看出是应用还是数据库。"""
    from sqlalchemy import text

    from app.db import engine

    db_ok, db_err = True, ""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_ok, db_err = False, str(exc)[:200]
    return {"ok": True, "build": build_id(), "db": db_ok, "db_error": db_err}
