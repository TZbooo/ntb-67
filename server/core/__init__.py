# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
ntb-67 core package.

Core server components and utilities for the NTB-67 reverse tunneling
service. This package provides abstractions and helpers used by the
server application to manage tunnel sessions, route incoming HTTP
requests to active tunnels, and generate/validate temporary signed
subdomains.

Importing this package has no side effects; its modules expose classes
and functions intended to be used by server entry points and application
initialization code.
"""

from .reverse_proxy_server import ReverseProxyServer

__all__ = ["ReverseProxyServer"]
