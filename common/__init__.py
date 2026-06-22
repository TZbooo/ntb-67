# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Общие утилиты и вспомогательные функции для проекта ntb-67.

Данный пакет содержит разделяемую логику между клиентом и сервером, включая
инструменты для двустороннего проксирования трафика и безопасного закрытия сокетов.
"""

from common.utils import close_writer, pipe

__all__ = ["close_writer", "pipe"]
