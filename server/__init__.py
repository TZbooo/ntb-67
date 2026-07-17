# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Server-side package for the asynchronous ntb-67 tunneling service.

This package handles external traffic routing (Control and Data Plane),
management of active subdomain sessions, socket multiplexing, and coordination
of connected CLI clients.
"""
