# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Файл определения локальных, для модуля логики телеграм-интерфейса, моделей данных."""

import secrets

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.database import Base


def generate_api_key() -> str:
    """Генерирует криптографически безопасный случайный токен для API."""
    return f"ntb_{secrets.token_urlsafe(32)}"


class TelegramUser(Base):
    """Модель пользователя, зарегистрированного через Telegram-бота."""

    __tablename__ = "telegram_users"

    tg_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, unique=True, nullable=False
    )

    api_key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, default=generate_api_key
    )

    max_tunnels: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    subdomains: Mapped[list["UserSubdomain"]] = relationship(
        "UserSubdomain", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """Возвращает строковое представление объекта TelegramUser для отладки и логов."""
        return (
            f"<TelegramUser tg_id={self.tg_id} max_tunnels={self.max_tunnels}>"
        )


class UserSubdomain(Base):
    """Модель выделенного пользователю поддомена для маршрутизации."""

    __tablename__ = "user_subdomains"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    subdomain: Mapped[str] = mapped_column(
        String(63), unique=True, nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("telegram_users.tg_id", ondelete="CASCADE"),
        nullable=False,
    )

    user: Mapped["TelegramUser"] = relationship(
        "TelegramUser", back_populates="subdomains"
    )

    def __repr__(self) -> str:
        """Возвращает строковое представление объекта UserSubdomain."""
        return f"<UserSubdomain id={self.id} subdomain={self.subdomain} user_id={self.user_id}>"
