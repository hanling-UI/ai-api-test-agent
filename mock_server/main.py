"""被测服务（mock）：一个「电商 API」，故意埋了 3 个 bug 供演示。

Bug 1：POST /users 缺少 name 时返回 500（应 400）
Bug 2：GET /orders/{id} 不校验 token（应 401）
Bug 3：GET /users?page=-1 返回 500（应 400）
"""
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Mock Shop API", version="1.0.0")

USERS = {1: {"id": 1, "name": "Alice", "email": "a@demo.com"}}
ORDERS = {1: {"id": 1, "user_id": 1, "amount": 99.0, "status": "paid"}}
PRODUCTS = {1: {"id": 1, "name": "键盘", "price": 299.0}}


class UserIn(BaseModel):
    email: str
    name: str | None = None  # 故意设成可选，触发 bug 1


class OrderIn(BaseModel):
    user_id: int
    amount: float


def require_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未授权")
    return authorization.split(" ", 1)[1]


def _auth_optional(authorization: str | None = Header(default=None)) -> str | None:
    """故意不校验：bug 2 的来源。"""
    return authorization


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/login")
def login(email: str, password: str = "demo1234"):
    if "@" not in email:
        raise HTTPException(400, "邮箱格式错误")
    return {"token": "mock-token", "user": {"email": email}}


@app.get("/users")
def list_users(page: int = 1, size: int = 10):
    if page < 1:
        raise RuntimeError("page must be >= 1")  # bug 3：未转成 400
    items = list(USERS.values())[:size]
    return {"page": page, "size": size, "total": len(USERS), "items": items}


@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = USERS.get(user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    return user


@app.post("/users")
def create_user(payload: UserIn, _token: str = Depends(require_token)):
    if not payload.name:
        raise KeyError("name")  # bug 1：未校验，抛出 500
    new_id = max(USERS) + 1
    USERS[new_id] = {"id": new_id, "name": payload.name, "email": payload.email}
    return USERS[new_id]


@app.put("/users/{user_id}")
def update_user(user_id: int, payload: UserIn, _token: str = Depends(require_token)):
    if user_id not in USERS:
        raise HTTPException(404, "用户不存在")
    USERS[user_id]["email"] = payload.email
    if payload.name:
        USERS[user_id]["name"] = payload.name
    return USERS[user_id]


@app.delete("/users/{user_id}")
def delete_user(user_id: int, _token: str = Depends(require_token)):
    if user_id not in USERS:
        raise HTTPException(404, "用户不存在")
    USERS.pop(user_id)
    return {"deleted": user_id}


@app.get("/products")
def list_products():
    return {"items": list(PRODUCTS.values()), "total": len(PRODUCTS)}


@app.get("/products/{product_id}")
def get_product(product_id: int):
    product = PRODUCTS.get(product_id)
    if product is None:
        raise HTTPException(404, "商品不存在")
    return product


@app.post("/orders")
def create_order(payload: OrderIn, _token: str = Depends(require_token)):
    if payload.user_id not in USERS:
        raise HTTPException(400, "用户不存在")
    new_id = max(ORDERS) + 1
    ORDERS[new_id] = {"id": new_id, "user_id": payload.user_id,
                      "amount": payload.amount, "status": "created"}
    return ORDERS[new_id]


@app.get("/orders")
def list_orders(_token: str = Depends(require_token)):
    return {"items": list(ORDERS.values()), "total": len(ORDERS)}


@app.get("/orders/{order_id}")
def get_order(order_id: int, _ignored: str | None = Depends(_auth_optional)):
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(404, "订单不存在")
    return order  # bug 2：不校验 token，未登录也能读


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9000)
