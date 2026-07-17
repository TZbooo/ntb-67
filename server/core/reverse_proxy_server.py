# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Server application for multi-user reverse tunneling.

This module implements an asynchronous server that dynamically assigns
subdomains to clients, parses incoming Host headers, and routes traffic from
Nginx to the appropriate tunnels.
"""

import asyncio

from common.utils import close_writer, pipe
from server.database import get_db_session
from server.tg_bot.crud import get_telegram_user_by

from .http_utils import extract_subdomain
from .models import TunnelRegistry
from .security import generate_free_subdomain, is_valid_subdomain


class ReverseProxyServer:
    """Tunnel server that coordinates traffic based on subdomains."""

    def __init__(self):
        """Initialize ReverseProxyServer with a registry of active subdomains."""
        self.active_tunnels = TunnelRegistry()

    async def handle_client_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """
        Handle control and data connections from an NTB client.

        The method classifies the incoming request by its initial marker. An
        ``INIT`` message starts or restores the control session, while a
        ``DATA`` message registers a socket pair for later proxying.

        Args:
        ----
            reader: The socket's asynchronous reading stream.
            writer: The socket's asynchronous writing stream.

        """
        subdomain = None
        line = ""
        try:
            line_bytes = await reader.readline()
            if not line_bytes:
                return
            line = line_bytes.decode("utf-8").strip()

            if line.startswith("INIT:"):
                parts = line.split(":")
                api_key = parts[1].strip()
                requested_subdomain = (
                    parts[2].strip() if len(parts) > 2 else None
                )

                if not await self._authenticate_user(api_key):
                    print(
                        f"🚫 Rejected: connection attempt with an invalid API key: {api_key[:10]}..."
                    )
                    writer.write(b"ERROR:Invalid API Key\n")
                    await writer.drain()
                    await close_writer(writer)
                    return

                if requested_subdomain:
                    if is_valid_subdomain(requested_subdomain):
                        if self.active_tunnels.contains(requested_subdomain):
                            subdomain = requested_subdomain
                            print(f"✅ Resuming existing tunnel: {subdomain}")
                        else:
                            # The domain is ours, but the session in memory has already expired.
                            # Recreate the structure with the same name.
                            subdomain = requested_subdomain
                            self.active_tunnels.register(subdomain)
                            print(
                                f"⏳ Session expired, but the domain is valid. Recreating tunnel: {subdomain}"
                            )
                    else:
                        print(
                            f"⚠️ Client attempted to claim a domain (possible abuse): {requested_subdomain}"
                        )
                if not subdomain:
                    subdomain = (
                        generate_free_subdomain()
                    )  # Generate a new subdomain for the client
                    while self.active_tunnels.contains(subdomain):
                        subdomain = generate_free_subdomain()

                    print(f"🚀 Registering a new free tunnel: {subdomain}")
                    self.active_tunnels.register(subdomain)
                self.active_tunnels.activate_control(subdomain, writer)
                # Send the generated subdomain back to the client
                writer.write(f"ASSIGNED:{subdomain}\n".encode("utf-8"))
                await writer.drain()

                while True:
                    # Wait for a keep-alive or new commands from the client. Timeout: 10 minutes.
                    data = await asyncio.wait_for(
                        reader.read(1024), timeout=10 * 60.0
                    )

                    if data == b"":
                        # The client closed the socket gracefully on its side
                        print(
                            f"🔌 Client {subdomain} closed the connection gracefully."
                        )
                        break

            # If the client opened a socket for forwarding traffic
            elif line.startswith("DATA:"):
                subdomain = line.split(":", 1)[1].strip()
                if self.active_tunnels.contains(subdomain):
                    await self.active_tunnels.get(subdomain).data_queue.put(
                        (reader, writer)
                    )
                    print(
                        f"📦 Data socket added to the queue for subdomain: {subdomain}"
                    )
                else:
                    print(f"⚠️ Data token for an unknown subdomain: {subdomain}")
                    await close_writer(writer)

        except (asyncio.TimeoutError, ConnectionResetError):
            print(
                f"⏱️ The control connection for tunnel {subdomain} dropped due to timeout or disconnect."
            )
        except Exception as e:
            print(f"❌ Error while handling client ({subdomain}): {e}")
        finally:
            # This block executes only in two cases:
            # 1. An exception occurred (inside INIT or DATA)
            # 2. The loop that kept the tunnel alive exited via break
            # If this was a successful DATA socket, we returned earlier and this block is skipped.
            if subdomain and line.startswith("INIT"):
                print(self.active_tunnels)
                print(f"🧹 Cleaning up resources for subdomain: {subdomain}")
                if self.active_tunnels.contains(subdomain):
                    self.active_tunnels.remove(subdomain)
                await close_writer(writer)

    async def handle_web_request(
        self, web_reader: asyncio.StreamReader, web_writer: asyncio.StreamWriter
    ) -> None:
        """
        Route an incoming HTTP request from Nginx to the tunnel client.

        The method reads the initial HTTP headers, extracts the target subdomain,
        asks the client to create a new transport socket pair over the control
        channel, and initiates a bidirectional data bridge.

        Args:
        ----
            web_reader: Read stream from the reverse proxy (Nginx).
            web_writer: Write stream to the reverse proxy (Nginx).

        """
        try:
            # Read the first chunk of data to extract the HTTP headers
            header_chunk = await web_reader.readuntil(b"\r\n\r\n")
        except Exception:
            await close_writer(web_writer)
            return

        # Look for the Host header in the bytes
        subdomain = extract_subdomain(header_chunk)

        if not subdomain or not self.active_tunnels.contains(subdomain):
            print(
                f"🚫 Request for an unknown or offline subdomain: {subdomain}.24tunl.ru"
            )
            # Return a neat 404 placeholder
            html_body = b"<h1>404 Tunnel Not Found</h1><p>ntb-67: Active tunnel for this subdomain not found.</p>"
            response = (
                b"HTTP/1.1 404 Not Found\r\n"
                b"Content-Type: text/html; charset=utf-8\r\n"
                b"Content-Length: " + str(len(html_body)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + html_body
            )
            web_writer.write(response)
            await web_writer.drain()
            await close_writer(web_writer)
            return

        # If the tunnel is online, ask it for a DATA connection
        tunnel = self.active_tunnels.get(subdomain)
        # Ensure the tunnel has a control connection
        if not tunnel.control:
            print(
                f"❌ The client control connection for {subdomain} is missing"
            )
            await close_writer(web_writer)
            return

        try:
            tunnel.control.write(b"REQUEST_CONN\n")
            await tunnel.control.drain()
        except Exception:
            print(
                f"❌ Failed to send a socket request to the client for {subdomain}"
            )
            await close_writer(web_writer)
            return

        try:
            data_reader, data_writer = await asyncio.wait_for(
                tunnel.data_queue.get(), timeout=5.0
            )
        except asyncio.TimeoutError:
            print(
                f"⏱️ Client {subdomain} did not allocate a socket in time for the request."
            )
            await close_writer(web_writer)
            return

        # Send the headers already read from the web socket to the tunnel first
        data_writer.write(header_chunk)
        await data_writer.drain()

        # Start the bridge
        await self.bridge(web_reader, web_writer, data_reader, data_writer)

    async def bridge(
        self,
        web_reader: asyncio.StreamReader,
        web_writer: asyncio.StreamWriter,
        data_reader: asyncio.StreamReader,
        data_writer: asyncio.StreamWriter,
    ) -> None:
        """
        Bridge traffic bidirectionally between the web socket and the client.

        The method runs two independent byte-streaming tasks through
        ``asyncio.gather`` and blocks until either side closes the session.

        Args:
        ----
            web_reader: Read stream from the web socket (user requests).
            web_writer: Write stream to the web socket (user responses).
            data_reader: Read stream from the tunnel socket (responses from the local host).
            data_writer: Write stream to the tunnel socket (requests to the local host).

        """
        await asyncio.gather(
            pipe(web_reader, data_writer), pipe(data_reader, web_writer)
        )

    async def _authenticate_user(self, api_key: str) -> bool:
        """Check whether the API key exists in PostgreSQL."""
        async with get_db_session() as session:
            user = await get_telegram_user_by(session, api_key=api_key)
            return user is not None
