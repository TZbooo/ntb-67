# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Dependencies and context for securing and operating the REST API."""

import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from server.core.reverse_proxy_server import ReverseProxyServer

X_TOKEN_HEADER = APIKeyHeader(name="X-NTB-Admin-Token", auto_error=False)


class APIContext:
    """Provide access to the global TCP server context."""

    _server_instance: ReverseProxyServer | None = None

    @classmethod
    def init(cls, server: ReverseProxyServer) -> None:
        """
        Initialize the context with the running TCP server instance.

        Args:
        ----
            server: The currently running proxy server instance.

        """
        cls._server_instance = server

    @classmethod
    def get_server(cls) -> ReverseProxyServer:
        """
        Return the current TCP server instance for endpoint usage.

        Returns
        -------
            The current ReverseProxyServer instance.

        Raises
        ------
            RuntimeError: If the context has not been initialized.

        """
        if cls._server_instance is None:
            raise RuntimeError("APIContext has not been initialized.")
        return cls._server_instance


async def verify_admin_token(token: str = Security(X_TOKEN_HEADER)) -> str:
    """
    Validate the authorization token from the request headers.

    Args:
    ----
        token: The token supplied in the X-NTB-Admin-Token header.

    Returns:
    -------
        The validated authorization token.

    Raises:
    ------
        HTTPException: If the token is missing or does not match the expected value.

    """
    expected_token = os.getenv("NTB_ADMIN_TOKEN", "fallback_secret_token")
    if not token or token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token.",
        )
    return token
