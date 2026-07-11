# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
FastAPI daemon for the NTB-67 tunnel client.

This module wires the tunnel client lifecycle into a small local API that
exposes the current status for the terminal UI and other monitoring tools.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from .core import NTBClient


class ClientStatusResponse(BaseModel):
    """Schema describing the current tunnel status returned by the local API."""

    server_host: str
    server_port: int
    local_port: int
    public_url: str | None
    subdomain: str | None
    error: str | None


@asynccontextmanager
async def global_lifespan(app_instance: FastAPI):
    """Start and stop the NTB tunnel client alongside the FastAPI application."""
    config = getattr(app_instance.state, "tunnel_config", None)
    if not config:
        raise RuntimeError(
            "The tunnel_config has not been provided in app.state!"
        )

    client = NTBClient(
        server_host=config["host"],
        server_port=config["port"],
        local_port=config["local_port"],
        api_key=config["api_key"],
    )

    app_instance.state.ntb_client = client

    client_task = asyncio.create_task(client.start())

    yield

    client_task.cancel()
    try:
        await client_task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=global_lifespan)


@app.get("/api/client/status", response_model=ClientStatusResponse)
async def get_client_status():
    """Return the current tunnel state in a serializable API response."""
    client: NTBClient = app.state.ntb_client

    public_url = (
        f"https://{client.subdomain}.24tunl.ru" if client.subdomain else None
    )

    return ClientStatusResponse(
        server_host=client.server_host,
        server_port=client.server_port,
        local_port=client.local_port,
        public_url=public_url,
        subdomain=client.subdomain,
        error=client.error,
    )
