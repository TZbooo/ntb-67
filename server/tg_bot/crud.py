# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Определения CRUD-операций для работы с данными пользователя."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import TelegramUser


async def get_telegram_user(
    session: AsyncSession, tg_id: int
) -> TelegramUser | None:
    """
    Проверяет наличие пользователя в базе данных по его Telegram ID.

    Возвращает объект TelegramUser, если пользователь найден, иначе None.
    """
    query = select(TelegramUser).where(TelegramUser.tg_id == tg_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()
