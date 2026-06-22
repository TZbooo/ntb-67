# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Инициализация асинхронного движка и фабрики сессий SQLAlchemy.

Настраивает подключение к PostgreSQL через asyncpg, предоставляет базовый
класс для ORM-моделей и генератор зависимостей сессионного слоя для ntb-67.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей базы данных проекта ntb-67."""

    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Создает и изолирует асинхронную сессию базы данных.

    Используется в качестве контекстного менеджера или зависимости FastAPI.
    Автоматически фиксирует транзакцию при успешном завершении блока или
    выполняет откат изменений в случае исключения.

    Yields
    ------
        Экземпляр активной асинхронной сессии AsyncSession.

    Raises
    ------
        Exception: Любое исключение, возникшее в процессе выполнения транзакции.

    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
