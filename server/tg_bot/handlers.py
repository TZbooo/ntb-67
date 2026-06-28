# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Обработчики команд для Telegram-бота NTB-67."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

tg_bot_router = Router()


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Возвращает главную клавиатуру."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔑 Сгенерировать API-токен",
                    callback_data="generate_token",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📚 Документация",
                    url="https://github.com/TZbooo/ntb-67",
                )
            ],
        ]
    )


@tg_bot_router.message(CommandStart())
async def cmd_start(message: Message):
    """Приветственное сообщение."""
    await message.answer(
        "Привет! 👋\n\n"
        "Я бот платформы NTB-67 (Network Tunnel Broker).\n"
        "Здесь ты можешь получить API-ключ для управления своими туннелями в CI/CD.",
        reply_markup=get_main_keyboard(),
    )
