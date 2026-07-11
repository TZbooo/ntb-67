# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Utilities for generating and validating temporary tunnel subdomains.

The module creates signed subdomain values using HMAC-SHA256 and verifies
that they are still within their allowed lifetime, protecting the tunnel
service from forged or reused addresses.
"""

import hashlib
import hmac
import secrets
import time

from .config import project_settings


def generate_free_subdomain() -> str:
    """Generate a random subdomain with a timestamp and HMAC signature."""
    rand_bytes = secrets.token_hex(4)

    timestamp_hex = hex(int(time.time()))[2:]

    payload = f"{rand_bytes}:{timestamp_hex}"

    signature = hmac.new(
        project_settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:8]

    return f"{rand_bytes}-{timestamp_hex}-{signature}"


def is_valid_subdomain(subdomain: str) -> bool:
    """Validate the subdomain structure, signature, and expiration time."""
    if subdomain.count("-") != 2:
        return False

    rand_bytes, timestamp_hex, signature = subdomain.split("-", 2)

    payload = f"{rand_bytes}:{timestamp_hex}"
    expected_signature = hmac.new(
        project_settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:8]

    if not hmac.compare_digest(signature, expected_signature):
        return False

    try:
        created_time = int(timestamp_hex, 16)
    except ValueError:
        return False

    current_time = int(time.time())

    if current_time - created_time > project_settings.tunnel_live_time_seconds:
        print(
            f"⏱️ Subdomain {subdomain} has expired (created more than {project_settings.tunnel_live_time_seconds} seconds ago)"
        )
        return False

    return True
