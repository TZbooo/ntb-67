# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Data models used by the Telegram interface logic."""

import secrets

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.database import Base


def generate_api_key() -> str:
    """Generate a cryptographically secure random API token."""
    return f"ntb_{secrets.token_urlsafe(32)}"


class TelegramUser(Base):
    """Model for a user registered through the Telegram bot."""

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
        """Return a debugging-friendly string representation of TelegramUser."""
        return (
            f"<TelegramUser tg_id={self.tg_id} max_tunnels={self.max_tunnels}>"
        )


class UserSubdomain(Base):
    """Model for a subdomain assigned to a user for routing."""

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
        """Return a debugging-friendly string representation of UserSubdomain."""
        return f"<UserSubdomain id={self.id} subdomain={self.subdomain} user_id={self.user_id}>"
