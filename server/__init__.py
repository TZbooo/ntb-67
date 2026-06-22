# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Серверная часть асинхронного сервиса туннелирования ntb-67.

Данный пакет отвечает за логику маршрутизации внешнего трафика (Control и Data Plane),
управление активными сессиями поддоменов, мультиплексирование сокетов и координацию
подключенных CLI-клиентов.
"""

from server.proxy_server import NTBServer

__all__ = ["NTBServer"]
