"""临时验证用：一个带口令门禁的服务（模拟项目一的鉴权方式）。"""
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="Gated Demo")
PWD = "demo123"
COOKIE = "gated_access"
TOKEN = "tok-abc"


@app.post("/login")
def login(password: str = Form(...)):
    if password != PWD:
        raise HTTPException(401, "口令不正确")
    resp = JSONResponse({"ok": True})
    resp.set_cookie(COOKIE, TOKEN, httponly=True)
    return resp


@app.middleware("http")
async def gate(request, call_next):
    if request.url.path in ("/login",):
        return await call_next(request)
    if request.cookies.get(COOKIE) != TOKEN:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    return await call_next(request)


@app.get("/items")
def items():
    return [{"id": 1, "name": "item"}]


@app.post("/orders")
def create_order(user_id: int = 1):
    return {"id": 1, "user_id": user_id}
