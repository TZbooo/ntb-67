# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Authentication helpers for the admin interface."""

import os

from fastapi import Request
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select

from server.database import get_db_session
from server.models import User
from server.utils import verify_password


class AdminAuth(AuthenticationBackend):
    """Authentication backend for the admin panel."""

    async def login(self, request: Request) -> bool:
        """Authenticate a user from the admin login form."""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if (
            not username
            or not password
            or not isinstance(username, str)
            or not isinstance(password, str)
        ):
            return False

        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(
                    User.username == username,
                    User.is_active == True,  # noqa: E712
                )
            )
            user = result.scalars().first()

            if user and verify_password(password, user.hashed_password):
                request.session.update(
                    {"user_id": user.id, "username": user.username}
                )
                return True

        return False

    async def logout(self, request: Request) -> bool:
        """Clear the current user session."""
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """Check whether the current request is already authenticated."""
        token = request.session.get("user_id")
        return token is not None


secret_key = os.environ["SESSION_SECRET_KEY"]
authentication_backend = AdminAuth(secret_key=secret_key)
