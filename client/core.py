# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Core tunnel client implementation for NTB-67.

This module contains the asynchronous client logic responsible for opening
sessions with the remote tunnel server, establishing data channels, and
maintaining the control connection.
"""

import asyncio

from common.utils import close_writer, pipe


class NTBClient:
    """Client that manages the tunnel session and data-plane bridges."""

    def __init__(
        self, server_host: str, server_port: int, local_port: int, api_key: str
    ) -> None:
        """Initialize the client with server, local port, and authentication settings."""
        self.server_host = server_host
        self.server_port = server_port
        self.local_port = local_port
        self.api_key = api_key
        self.subdomain = None
        self.error = None

    async def open_connection(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open a low-level TCP connection to the NTB tunnel server."""
        return await asyncio.open_connection(self.server_host, self.server_port)

    async def start(self) -> None:
        """Maintain the tunnel session and reconnect automatically after failures."""
        while True:
            try:
                await self._start_tunnel()
            except Exception as e:
                print(f"❌ Connection error with the server: {e}")
                print("⏳ Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

    async def _start_tunnel(self) -> None:
        """Initialize the control-plane session and handle incoming server commands."""
        self.error = None
        reader, writer = await self.open_connection()

        if self.subdomain:
            writer.write(
                f"INIT:{self.api_key}:{self.subdomain}\n".encode("utf-8")
            )
            await writer.drain()
        else:
            writer.write(f"INIT:{self.api_key}\n".encode("utf-8"))
            await writer.drain()

        response_bytes = await reader.readline()
        if not response_bytes:
            await close_writer(writer)
            return

        response = response_bytes.decode("utf-8").strip()
        if response.startswith("ASSIGNED:"):
            self.subdomain = response.split(":", 1)[1].strip()

            print("\n" + "=" * 50)
            print("🎉 Tunnel started successfully!")
            print(f"🔗 Public address:  https://{self.subdomain}.24tunl.ru")
            print(f"🏠 Local port:   http://127.0.0.1:{self.local_port}")
            print("=" * 50 + "\n")
        elif response.startswith("ERROR:"):
            error_msg = response.split(":", 1)[1].strip()
            self.error = error_msg
            print(f"❌ The server returned an error: {error_msg}")
            await close_writer(writer)
            await asyncio.sleep(5)
            return
        else:
            print("❌ The server refused tunnel initialization.")
            await close_writer(writer)
            await asyncio.sleep(5)
            return

        heartbeat_task = asyncio.create_task(self.start_heartbeat(writer))

        try:
            while True:
                line_bytes = await reader.readline()
                if not line_bytes:
                    break

                cmd = line_bytes.decode("utf-8").strip()
                if cmd == "REQUEST_CONN":
                    asyncio.create_task(self.spawn_data_connection())
        finally:
            heartbeat_task.cancel()
            await close_writer(writer)

    async def spawn_data_connection(self) -> None:
        """Open a bridged data connection between the server and the local service."""
        try:
            server_reader, server_writer = await self.open_connection()
            server_writer.write(f"DATA:{self.subdomain}\n".encode("utf-8"))
            await server_writer.drain()

            local_reader, local_writer = await asyncio.open_connection(
                "127.0.0.1", self.local_port
            )

        except Exception as e:
            print(f"❌ Failed to establish data channels: {e}")
            return

        await asyncio.gather(
            pipe(server_reader, local_writer), pipe(local_reader, server_writer)
        )

    async def start_heartbeat(self, writer: asyncio.StreamWriter) -> None:
        """Send periodic keep-alive packets to prevent the control connection from timing out."""
        try:
            while True:
                await asyncio.sleep(10)
                writer.write(b"PING\n")
                await writer.drain()
        except Exception:
            pass
