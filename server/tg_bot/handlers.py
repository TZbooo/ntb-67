# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Command and message handlers for the Telegram bot integrated with the NTB-67 proxy server."""

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
    """Build the inline keyboard for the main menu."""
    buttons = [
        [
            InlineKeyboardButton(
                text="🔑 My API Key", callback_data="view_api_key"
            ),
            InlineKeyboardButton(
                text="🌐 My Tunnels", callback_data="view_tunnels"
            ),
        ],
        [
            InlineKeyboardButton(
                text="📚 Documentation", url="https://github.com/netbiom/ntb-67"
            ),
            InlineKeyboardButton(
                text="🔄 Refresh", callback_data="refresh_menu"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@tg_bot_router.message(CommandStart())
async def start(message: Message) -> None:
    """Handle /start by registering the user and showing an interactive greeting."""
    if message.from_user is None:
        await message.answer("❌ Error: could not determine your Telegram ID.")
        return

    async with get_db_session() as session:
        user = await get_telegram_user_by(session, tg_id=message.from_user.id)
        if not user:
            user = await create_telegram_user(session, message.from_user.id)

    welcome_text = (
        f"⚡ *Welcome to ntb-67 Proxy Server!*\n\n"
        f"Hello, {message.from_user.first_name}. You are successfully authenticated in the local tunnel system.\n\n"
        f"Use the menu below to manage your sessions and configurations."
    )

    await message.answer(
        text=welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(),
    )


@tg_bot_router.message(Command("menu"))
async def show_menu(message: Message) -> None:
    """Handle /menu to quickly open the control panel from anywhere."""
    await message.answer(
        text="🎛 *ntb-67 control panel:*",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(),
    )


@tg_bot_router.callback_query(F.data == "view_api_key")
async def callback_view_api_key(callback: CallbackQuery) -> None:
    """Display the API key in a monospaced format for easy copying."""
    # Guard against None: verify that the message exists and has an edit method
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
        f"🔑 *Your personal access token:*\n\n"
        f"`{user.api_key}`\n\n"
        f"⚠️ _Do not share this key with anyone. It is used to authenticate your local ntb-67 client._"
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
    """Show information about the user's available tunnel limits."""
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
        "🌐 *ntb-67 tunnel management*\n\n"
        f"📊 Your current limit: *{user.max_tunnels}* active tunnels.\n\n"
        "ℹ️ In the current MVP version, the list of active proxies is still under development. "
        "Traffic statistics, ping, and session shutdown controls will appear here soon.\n\n"
        "⭐️ *PRO tier (coming soon):* We are preparing paid subscriptions that will let you "
        "increase the limit and run more than one tunnel at the same time!"
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
    """Return the interface to the main menu state."""
    if not isinstance(callback.message, Message):
        await callback.answer(
            "❌ Ошибка: сообщение недоступно для редактирования.",
            show_alert=True,
        )
        return

    welcome_text = (
        "⚡ *Welcome to ntb-67 Proxy Server!*\n\n"
        "Use the menu below to manage your sessions and configurations."
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
