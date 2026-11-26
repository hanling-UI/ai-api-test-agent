"""大模型调用（OpenAI 兼容）。

注意：客户端是**懒加载**的。
如果把 AsyncOpenAI(...) 写在模块顶层，一旦没有 key 就会在 import 阶段抛异常，
整个应用都起不来（连不需要模型的页面也打不开）。这里改成第一次调用时才创建。
"""
import json
import re

from openai import AsyncOpenAI

from ..config import LLM_FAST, LLM_SMART, OPENAI_API_KEY, OPENAI_BASE_URL

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError("未配置 OPENAI_API_KEY，无法调用大模型")
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    return _client


def _extract_json(text: str):
    """模型有时会包 ```json``` 或加解释，这里做容错。"""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1).strip()
    starts = [i for i in (text.find("["), text.find("{")) if i >= 0]
    if starts:
        start = min(starts)
        if start > 0:
            text = text[start:]
    return json.loads(text)


async def chat_json(system: str, user: str, *, smart: bool = False) -> dict | list:
    model = LLM_SMART if smart else LLM_FAST
    resp = await get_client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    content = resp.choices[0].message.content or ""
    try:
        return _extract_json(content)
    except Exception:  # noqa: BLE001
        return {}


async def chat_text(system: str, user: str, *, smart: bool = False) -> str:
    model = LLM_SMART if smart else LLM_FAST
    resp = await get_client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""
