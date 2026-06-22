# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
# 
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription. 
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

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
        self._tunnels: dict[str, TunnelSession] = {}

    def get(self, subdomain: str) -> TunnelSession:
        return self._tunnels[subdomain]

    def register(self, subdomain: str) -> TunnelSession:
        session = TunnelSession(data_queue=asyncio.Queue())
        self._tunnels[subdomain] = session
        return session

    def activate_control(self, subdomain: str, writer: asyncio.StreamWriter) -> None:
        self._tunnels[subdomain].control = writer

    def remove(self, subdomain: str) -> None:
        self._tunnels.pop(subdomain, None)

    def contains(self, subdomain: str) -> bool:
        return subdomain in self._tunnels