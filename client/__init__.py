# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Client package for the NTB-67 tunneling service.

This package exposes the core tunnel client and related runtime components used
for session initialization, server command handling, and local traffic bridging.
"""

from client.core import NTBClient

__all__ = ["NTBClient"]
