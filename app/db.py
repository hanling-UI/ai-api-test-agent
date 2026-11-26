"""数据库连接与会话。"""
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import DATABASE_URL

logger = logging.getLogger(__name__)

# Postgres 必须设连接超时：否则数据库没起来时，启动会一直卡在
# "Waiting for application startup."，看起来像死机。
_connect_args = {"connect_timeout": 5} if DATABASE_URL.startswith("postgresql") else {}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
    connect_args=_connect_args,
    pool_timeout=5,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  确保模型已注册

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库就绪：%s", DATABASE_URL.split("@")[-1])
    except Exception as exc:  # noqa: BLE001
        # 不阻塞启动：页面能打开，接口会返回明确错误，比"卡住"好排查
        logger.error(
            "数据库连接失败：%s\n"
            "  检查：Docker 是否启动？容器 pgv 是否在运行？\n"
            "  命令：docker start pgv\n"
            "  连接串：%s",
            exc,
            DATABASE_URL,
        )
