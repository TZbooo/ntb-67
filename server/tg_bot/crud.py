# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Определения CRUD-операций для работы с данными пользователя."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import TelegramUser


async def get_telegram_user_by(
    session: AsyncSession, **kwargs: Any
) -> TelegramUser | None:
    """
    Универсальный метод поиска пользователя по любому переданному полю.

    Примеры использования:
    --------------------
    user = await get_user_by(session, tg_id=123456)
    user = await get_user_by(session, api_key="ntb_...")

    Parameters
    ----------
    session : AsyncSession
        Активная асинхронная сессия SQLAlchemy.
    **kwargs : Any
        Параметры фильтрации (например, tg_id=..., api_key=...).

    Returns
    -------
    TelegramUser | None
        Объект пользователя, если найден, иначе None.

    """
    query = select(TelegramUser).filter_by(**kwargs)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def create_telegram_user(
    session: AsyncSession, tg_id: int
) -> TelegramUser:
    """
    Создает новую запись пользователя Telegram с автоматически сгенерированным API-ключом.

    Parameters
    ----------
    session : AsyncSession
        Активная асинхронная сессия SQLAlchemy.
    tg_id : int
        Уникальный Telegram ID пользователя.

    Returns
    -------
    TelegramUser
        Объект созданного пользователя, включая сгенерированный API-ключ.

    Raises
    ------
    Exception
        Если при фиксации транзакции в базе данных возникла ошибка.

    """
    db_user = TelegramUser(tg_id=tg_id)
    session.add(db_user)
    await (
        session.flush()
    )  # Заставляет SQLAlchemy сгенерировать default-значения и ID
    return db_user
