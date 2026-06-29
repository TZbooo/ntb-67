# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Обработчики команд и сообщений для Telegram-бота, интегрированного с прокси-сервером NTB-67."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from server.database import get_db_session

from .crud import create_telegram_user, get_telegram_user_by

tg_bot_router = Router()


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Формирует инлайн-клавиатуру главного меню."""
    buttons = [
        [
            InlineKeyboardButton(
                text="🔑 Мой API Ключ", callback_data="view_api_key"
            ),
            InlineKeyboardButton(
                text="🌐 Мои Туннели", callback_data="view_tunnels"
            ),
        ],
        [
            InlineKeyboardButton(
                text="📚 Документация", url="https://github.com/netbiom/ntb-67"
            ),
            InlineKeyboardButton(
                text="🔄 Обновить", callback_data="refresh_menu"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@tg_bot_router.message(CommandStart())
async def start(message: Message) -> None:
    """Обработчик команды /start. Регистрирует юзера и выводит интерактивное приветствие."""
    if message.from_user is None:
        await message.answer(
            "❌ Ошибка: не удалось определить ваш Telegram ID."
        )
        return

    async with get_db_session() as session:
        user = await get_telegram_user_by(session, tg_id=message.from_user.id)
        if not user:
            user = await create_telegram_user(session, message.from_user.id)

    welcome_text = (
        f"⚡ *Добро пожаловать в ntb-67 Proxy Server!*\n\n"
        f"Привет, {message.from_user.first_name}. Ты успешно авторизован в системе локальных туннелей.\n\n"
        f"Используй меню ниже для управления своими сессиями и конфигурациями."
    )

    await message.answer(
        text=welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(),
    )


@tg_bot_router.message(Command("menu"))
async def show_menu(message: Message) -> None:
    """Команда /menu для быстрого вызова панели управления из любого места."""
    await message.answer(
        text="🎛 *Панель управления ntb-67:*",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(),
    )


@tg_bot_router.callback_query(F.data == "view_api_key")
async def callback_view_api_key(callback: CallbackQuery) -> None:
    """Выводит API-ключ в моноширинном формате для удобного копирования."""
    # Защита от None: проверяем, что сообщение существует и у него есть метод редактирования
    if not isinstance(callback.message, Message):
        await callback.answer(
            "❌ Ошибка: сообщение недоступно для редактирования.",
            show_alert=True,
        )
        return

    async with get_db_session() as session:
        user = await get_telegram_user_by(session, tg_id=callback.from_user.id)

    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    text = (
        f"🔑 *Ваш персональный токен доступа:*\n\n"
        f"`{user.api_key}`\n\n"
        f"⚠️ _Никому не передавайте этот ключ. Он используется для аутентификации вашего локального клиента ntb-67._"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад в меню", callback_data="back_to_main"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        text=text, parse_mode="Markdown", reply_markup=keyboard
    )
    await callback.answer()


@tg_bot_router.callback_query(F.data == "view_tunnels")
async def callback_view_tunnels(callback: CallbackQuery) -> None:
    """Заглушка для будущего функционала управления активными туннелями."""
    if not isinstance(callback.message, Message):
        await callback.answer(
            "❌ Ошибка: сообщение недоступно для редактирования.",
            show_alert=True,
        )
        return

    text = (
        "🌐 *Управление туннелями ntb-67*\n\n"
        "В текущей версии MVP вывод активных прокси находится в разработке.\n\n"
        "📡 _Скоро здесь появится статистика трафика, пинг и управление портами._"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад в меню", callback_data="back_to_main"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        text=text, parse_mode="Markdown", reply_markup=keyboard
    )
    await callback.answer()


@tg_bot_router.callback_query(F.data.in_({"back_to_main", "refresh_menu"}))
async def callback_back_to_main(callback: CallbackQuery) -> None:
    """Возвращает интерфейс в состояние главного меню."""
    if not isinstance(callback.message, Message):
        await callback.answer(
            "❌ Ошибка: сообщение недоступно для редактирования.",
            show_alert=True,
        )
        return

    welcome_text = (
        "⚡ *Добро пожаловать в ntb-67 Proxy Server!*\n\n"
        "Используй меню ниже для управления своими сессиями и конфигурациями."
    )
    try:
        await callback.message.edit_text(
            text=welcome_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard(),
        )
    except Exception:
        pass
    await callback.answer()
