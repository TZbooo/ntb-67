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

from .models import User, UserSubdomain


async def get_user_by(session: AsyncSession, **kwargs: Any) -> User | None:
    """
    Look up a User by any supplied field.

    Examples:
    --------
        user = await get_user_by(session, api_key="ntb_...")

    Args:
    ----
        session: An active SQLAlchemy async session.
        **kwargs: Filter parameters such as tg_id or api_key.

    Returns:
    -------
        The User object if found, otherwise None.

    """
    query = select(User).filter_by(**kwargs)
    result = await session.execute(query)
    return result.scalar_one_or_none()


def create_subdomain(session: AsyncSession, user: User, subdomain: str) -> None:
    """
    Create a new subdomain for a given user.

    Args:
    ----
        session: An active SQLAlchemy async session.
        user: The User object to associate the subdomain with.
        subdomain: The desired subdomain string.

    Raises:
    ------
        ValueError: If the subdomain is already taken by another user.

    """
    user_subdomain_obj = UserSubdomain(subdomain=subdomain, user_id=user.id)
    session.add(user_subdomain_obj)


async def remove_subdomain(
    session: AsyncSession, user: User, subdomain: str
) -> None:
    """
    Remove a subdomain associated with a given user.

    Args:
    ----
        session: An active SQLAlchemy async session.
        user: The User object associated with the subdomain.
        subdomain: The subdomain string to be removed.

    Raises:
    ------
        ValueError: If the subdomain does not exist for the given user.

    """
    query = select(UserSubdomain).filter_by(
        subdomain=subdomain, user_id=user.id
    )
    result = await session.execute(query)
    user_subdomain_obj = result.scalar_one_or_none()

    if not user_subdomain_obj:
        raise ValueError(
            f"Subdomain '{subdomain}' does not exist for user '{user.username}'."
        )

    await session.delete(user_subdomain_obj)
