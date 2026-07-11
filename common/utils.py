# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Helper utilities for working with asyncio stream sockets.

This module provides low-level tools for safely closing sockets and piping
bytes from one stream to another.
"""

import asyncio


async def close_writer(writer: asyncio.StreamWriter) -> None:
    """Close a stream writer safely and suppress any cleanup errors."""
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:
        pass


async def pipe(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    """Stream bytes from a reader to a writer until EOF or a transport error."""
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        await close_writer(writer)
