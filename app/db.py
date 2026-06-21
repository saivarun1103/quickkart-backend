from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)

from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager

from app.config import DATABASE_URL


# -------------------------
# DATABASE URL
# -------------------------

ASYNC_DATABASE_URL = DATABASE_URL.replace(
    "postgresql://",
    "postgresql+asyncpg://"
).replace("sslmode=require", "ssl=require")


# -------------------------
# ENGINE (Singleton)
# -------------------------

engine = create_async_engine(
    ASYNC_DATABASE_URL,

    pool_size=20,
    max_overflow=20,

    pool_timeout=30,
    pool_recycle=1800,

    pool_pre_ping=True,

    echo=False
)


# -------------------------
# SESSION FACTORY
# -------------------------

SessionLocal = async_sessionmaker(
    bind=engine,

    class_=AsyncSession,

    autoflush=False,
    expire_on_commit=False
)


# -------------------------
# BASE
# -------------------------

Base = declarative_base()


# -------------------------
# FASTAPI DB DEPENDENCY
# -------------------------

async def get_db():

    async with SessionLocal() as db:
        yield db


# -------------------------
# CONTEXT MANAGER
# -------------------------

@asynccontextmanager
async def get_db_context():

    async with SessionLocal() as db:
        yield db

# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base
# from app.config import DATABASE_URL
# from contextlib import contextmanager

# engine = create_engine(
#     DATABASE_URL,
#     pool_size=10,
#     max_overflow=20,
#     pool_timeout=30,
#     pool_recycle=1800,
#     pool_pre_ping=True
# )


# SessionLocal = sessionmaker(
#     autocommit=False,
#     autoflush=False,
#     bind=engine
# )


# Base = declarative_base()

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# @contextmanager
# def get_db_context():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()