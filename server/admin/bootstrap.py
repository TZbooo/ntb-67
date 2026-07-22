# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Bootstrap helpers for creating the initial admin user."""

import os

from sqlalchemy import select

from server.database import get_db_session
from server.models import Role, User
from server.utils import hash_password


async def init_first_superuser():
    """Create base roles and the first super administrator if the DB is empty."""
    async with get_db_session() as session:
        result = await session.execute(select(User))
        existing_user = result.scalars().first()

        if existing_user:
            return

        print("⚡ Initializing database: creating the super administrator...")

        role_result = await session.execute(
            select(Role).where(Role.name == "super_admin")
        )
        super_role = role_result.scalars().first()

        if not super_role:
            super_role = Role(name="super_admin", permissions=["*"])
            session.add(super_role)
            await session.flush()

        admin_username = os.environ["FIRST_SUPERUSER_USERNAME"]
        admin_password = os.environ["FIRST_SUPERUSER_PASSWORD"]

        superuser = User(
            username=admin_username,
            hashed_password=hash_password(admin_password),
            is_active=True,
            role_id=super_role.id,
        )
        session.add(superuser)

        print(
            f"✅ Super administrator '{admin_username}' created successfully!"
        )
