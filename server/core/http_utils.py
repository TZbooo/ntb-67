# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Utilities for parsing incoming HTTP traffic.

This module provides helpers for analyzing raw byte chunks and extracting
HTTP information needed for correct routing inside the NTB-67 infrastructure.
"""


def extract_subdomain(
    header_chunk: bytes, base_domain: str = ".24tunl.ru"
) -> str | None:
    """Extract the target subdomain from the Host header in a raw HTTP request."""
    try:
        headers_text = header_chunk.decode("utf-8", errors="ignore")
        for line in headers_text.split("\r\n"):
            if line.lower().startswith("host:"):
                host_value = line.split(":", 1)[1].strip()
                if base_domain in host_value:
                    return host_value.split(base_domain)[0].lower()
                return host_value.split(".")[0].lower()
    except Exception:
        pass
    return None
