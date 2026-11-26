"""集中配置：从环境变量读取，带默认值。"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@127.0.0.1:5433/postgres",
)
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv(
    "OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
LLM_FAST = os.getenv("LLM_FAST", "qwen-flash")
LLM_SMART = os.getenv("LLM_SMART", "qwen-plus")

TARGET_BASE_URL = os.getenv("TARGET_BASE_URL", "http://127.0.0.1:9000")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo1234")

STATIC_DIR = BASE_DIR / "static"

