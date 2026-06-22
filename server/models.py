# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Управление реестром активных сетевых туннелей.

Данный модуль предоставляет абстракции для безопасного отслеживания сессий,
связывания управляющих соединений (Control Plane) и хранения асинхронных
очередей передачи данных (Data Plane) для проекта ntb-67.
"""

import asyncio
from dataclasses import dataclass


@dataclass
class TunnelSession:
    """Представляет активную сессию туннеля клиента."""

    data_queue: asyncio.Queue[tuple[asyncio.StreamReader, asyncio.StreamWriter]]
    control: asyncio.StreamWriter | None = None


class TunnelRegistry:
    """Инкапсулирует хранилище активных туннелей."""

    def __init__(self):
        """Инициализирует пустой реестр туннелей."""
        self._tunnels: dict[str, TunnelSession] = {}

    def get(self, subdomain: str) -> TunnelSession:
        """
        Возвращает активную сессию туннеля по его поддомену.

        Args:
        ----
            subdomain: Уникальное имя зарегистрированного поддомена.

        Returns:
        -------
            Объект TunnelSession, содержащий очереди данных и control-сокет.

        Raises:
        ------
            KeyError: Если туннель для указанного поддомена не найден.

        """
        return self._tunnels[subdomain]

    def register(self, subdomain: str) -> TunnelSession:
        """
        Создает и регистрирует новую сессию туннеля.

        Args:
        ----
            subdomain: Уникальное имя выделяемого поддомена.

        Returns:
        -------
            Инициализированный и сохраненный объект TunnelSession.

        """
        session = TunnelSession(data_queue=asyncio.Queue())
        self._tunnels[subdomain] = session
        return session

    def activate_control(
        self, subdomain: str, writer: asyncio.StreamWriter
    ) -> None:
        """
        Привязывает активный управляющий сокет к сессии поддомена.

        Используется при первичной регистрации или при бесшовном переподключении
        клиента в случае кратковременного сбоя сети.

        Args:
        ----
            subdomain: Имя поддомена, для которого обновляется соединение.
            writer: Асинхронный поток записи (StreamWriter) служебного канала.

        """
        self._tunnels[subdomain].control = writer

    def remove(self, subdomain: str) -> None:
        """
        Удаляет сессию туннеля из реестра и освобождает поддомен.

        Args:
        ----
            subdomain: Имя поддомена, который необходимо закрыть.

        """
        self._tunnels.pop(subdomain, None)

    def contains(self, subdomain: str) -> bool:
        """
        Проверяет, зарегистрирован ли указанный поддомен в системе.

        Args:
        ----
            subdomain: Проверяемое имя поддомена.

        Returns:
        -------
            True, если сессия активна, иначе False.

        """
        return subdomain in self._tunnels
