# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Обработчики команд и сообщений для Telegram-бота, интегрированного с прокси-сервером NTB-67."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from server.database import get_db_session

from .crud import create_telegram_user, get_telegram_user

tg_bot_router = Router()


@tg_bot_router.message(CommandStart())
async def start(message: Message) -> None:
    """Обработчик команды /start для Telegram-бота."""
    if message.from_user is None:
        print("Ошибка: message.from_user is None")
        await message.answer(
            "Ошибка: не удалось определить пользователя. Обратитесь в поддержку."
        )
        return

    print(
        f"Получено сообщение /start от пользователя {message.from_user.id} ({message.from_user.username})"
    )
    async with get_db_session() as session:
        user = await get_telegram_user(session, message.from_user.id)

        if user:
            print(f"Пользователь найден: {user.api_key}")
        else:
            user = await create_telegram_user(session, message.from_user.id)
            print(f"Пользователь создан: {user.api_key}")

        await message.answer(
            f"Привет, {message.from_user.first_name}! Ваш API-ключ: {user.api_key}"
        )
