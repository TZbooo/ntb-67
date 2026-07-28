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

from .models import User


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
