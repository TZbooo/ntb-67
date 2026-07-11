# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""CRUD definitions for working with Telegram user data."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import TelegramUser


async def get_telegram_user_by(
    session: AsyncSession, **kwargs: Any
) -> TelegramUser | None:
    """
    Look up a Telegram user by any supplied field.

    Examples:
    --------
        user = await get_user_by(session, tg_id=123456)
        user = await get_user_by(session, api_key="ntb_...")

    Args:
    ----
        session: An active SQLAlchemy async session.
        **kwargs: Filter parameters such as tg_id or api_key.

    Returns:
    -------
        The TelegramUser object if found, otherwise None.

    """
    query = select(TelegramUser).filter_by(**kwargs)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def create_telegram_user(
    session: AsyncSession, tg_id: int
) -> TelegramUser:
    """
    Create a new Telegram user record with an automatically generated API key.

    Args:
    ----
        session: An active SQLAlchemy async session.
        tg_id: The user's unique Telegram ID.

    Returns:
    -------
        The created TelegramUser object, including the generated API key.

    """
    db_user = TelegramUser(tg_id=tg_id)
    session.add(db_user)
    await (
        session.flush()
    )  # Force SQLAlchemy to generate default values and an ID
    return db_user
