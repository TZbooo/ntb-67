# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Terminal UI for monitoring the NTB-67 tunnel client.

The module renders a lightweight Textual interface that shows the current
local endpoint, remote server address, and public tunnel URL.
"""

from typing import Any

import httpx
from rich.columns import Columns
from textual.app import App, ComposeResult
from textual.widgets import Footer, Label


class TerminalUserInterface(App[Any]):
    """Textual-based terminal UI for displaying tunnel status."""

    CSS = """
    #logo {
        color: green;
        text-style: bold;
        margin: 1 0 0 3;
        padding: 0;
    }

    #status_label {
        margin: 1 3;
    }
    """
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, api_url: str, **kwargs: Any) -> None:
        """Initialize the UI and prepare the HTTP client for status polling."""
        super().__init__(**kwargs)
        self.api_url = f"{api_url.rstrip('/')}/api/client/status"
        self.http_client = httpx.AsyncClient()

    def compose(self) -> ComposeResult:
        """Create the visual layout of the terminal interface."""
        yield Label("ntb-67", id="logo")
        yield Label("[ ] Connecting to the API...", id="status_label")
        yield Footer()

    def on_mount(self) -> None:
        """Start periodic status updates after the UI is mounted."""
        self.set_interval(2.0, self.update_status)

    async def update_status(self) -> None:
        """Fetch the current tunnel state from the local daemon API and refresh the view."""
        try:
            response = await self.http_client.get(self.api_url)
            if response.status_code == 200:
                data = response.json()

                local_val = f"127.0.0.1:{data['local_port']}"
                server_val = f"{data['server_host']}:{data['server_port']}"

                if data.get("subdomain"):
                    public_val = data["public_url"]
                elif data.get("error"):
                    public_val = f"[!] Error: {data['error']}"
                else:
                    public_val = "[-] Waiting for a subdomain assignment..."

                col1 = [
                    "Local service address:",
                    "Remote NTB server:",
                    "Public address:",
                ]
                col2: list[str] = [local_val, server_val, public_val]

                renderable = Columns(
                    ["\n".join(col1), "\n".join(col2)], padding=(0, 12)
                )

                self.query_one("#status_label", Label).update(renderable)

            else:
                self.query_one("#status_label", Label).update(
                    f"[!] The API returned an error: {response.status_code}"
                )
        except httpx.RequestError:
            self.query_one("#status_label", Label).update(
                "[-] Waiting for the API server to start..."
            )

    async def action_quit(self) -> None:
        """Close the HTTP client gracefully before exiting the UI."""
        await self.http_client.aclose()
        await super().action_quit()
