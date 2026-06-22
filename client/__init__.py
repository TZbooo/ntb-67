# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Клиентская часть сервиса туннелирования ntb-67.

Данный пакет содержит логику инициализации сессий, обработки управляющих команд
от сервера маршрутизации и проброса сетевого трафика на локальные порты.
"""

from client.tunnel_client import NTBClient

__all__ = ["NTBClient"]
