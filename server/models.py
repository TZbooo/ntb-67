# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Database models for users and roles."""

from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .utils import generate_api_key


class Role(Base):
    """Represents a user role with permissions."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String, unique=True, nullable=False)
    permissions: Mapped[dict[str, Any]] = mapped_column(
        sa.JSON, nullable=False, default=[]
    )

    users: Mapped[list["User"]] = relationship("User", back_populates="role")


class User(Base):
    """Represents an application user linked to a role."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    username: Mapped[str] = mapped_column(
        sa.String, unique=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(sa.String, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True)

    role_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("roles.id"), nullable=False
    )
    role: Mapped["Role"] = relationship("Role", back_populates="users")

    api_key: Mapped[str] = mapped_column(
        sa.String(64), unique=True, nullable=False, default=generate_api_key
    )
    max_tunnels: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=1
    )
    subdomains: Mapped[list["UserSubdomain"]] = relationship(
        "UserSubdomain", back_populates="user", cascade="all, delete-orphan"
    )


class UserSubdomain(Base):
    """Model for a subdomain assigned to a user for routing."""

    __tablename__ = "user_subdomains"

    id: Mapped[int] = mapped_column(
        sa.Integer, primary_key=True, autoincrement=True
    )

    subdomain: Mapped[str] = mapped_column(
        sa.String(63), unique=True, nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="subdomains")
