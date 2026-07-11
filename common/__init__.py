# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Shared utilities and helper functions for the NTB-67 project.

This package contains logic shared between the client and server, including
helpers for bidirectional traffic proxying and safe socket closure.
"""

from common.utils import close_writer, pipe

__all__ = ["close_writer", "pipe"]
