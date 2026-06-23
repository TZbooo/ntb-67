# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Зависимости и контекст для обеспечения безопасности и работы REST API."""

import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from server.proxy_server import NTBServer

X_TOKEN_HEADER = APIKeyHeader(name="X-NTB-Admin-Token", auto_error=False)


class APIContext:
    """Обеспечивает доступ к глобальному контексту TCP-сервера."""

    _server_instance: NTBServer | None = None

    @classmethod
    def init(cls, server: NTBServer) -> None:
        """
        Инициализирует контекст инстансом запущенного TCP-сервера.

        Args:
        ----
            server: Текущий работающий экземпляр прокси-сервера.

        """
        cls._server_instance = server

    @classmethod
    def get_server(cls) -> NTBServer:
        """
        Возвращает текущий инстанс TCP-сервера для работы эндпоинтов.

        Returns
        -------
            Текущий работающий экземпляр NTBServer.

        Raises
        ------
            RuntimeError: Если контекст не был предварительно инициализирован.

        """
        if cls._server_instance is None:
            raise RuntimeError("APIContext не был инициализирован.")
        return cls._server_instance


async def verify_admin_token(token: str = Security(X_TOKEN_HEADER)) -> str:
    """
    Проверяет токен авторизации из заголовков запроса.

    Args:
    ----
        token: Строковый токен, переданный в заголовке X-NTB-Admin-Token.

    Returns:
    -------
        Валидированный токен авторизации.

    Raises:
    ------
        HTTPException: Если токен отсутствует или не совпадает с эталонным.

    """
    expected_token = os.getenv("NTB_ADMIN_TOKEN", "fallback_secret_token")
    if not token or token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или отсутствующий админ-токен.",
        )
    return token
