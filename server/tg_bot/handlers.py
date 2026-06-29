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

tg_bot_router = Router()


@tg_bot_router.message(CommandStart())
async def start(message: Message) -> None:
    """Обработчик команды /start для Telegram-бота."""
    await message.answer("Привет!")
