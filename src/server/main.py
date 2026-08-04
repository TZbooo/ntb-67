# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Initialization and startup module for the NTB-67 proxy server.

It combines TCP socket management and the administrative REST API in a single
asynchronous event-driven loop.

Port layout:
    * :9000 — TCP control server (control socket for CLI clients)
    * :8000 — TCP web traffic server (receives incoming HTTP traffic from Nginx)
    * :8080 — FastAPI admin API (locally available management interface)
"""

import asyncio
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from sqladmin import Admin

from server.admin.auth import authentication_backend
from server.admin.bootstrap import init_first_superuser
from server.admin.views import RoleAdmin, UserAdmin, UserSubdomainAdmin
from server.api.dependencies import APIContext
from server.api.routes import router
from server.core import ReverseProxyServer
from server.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the FastAPI lifecycle by enabling and disabling the webhook."""
    await init_first_superuser()

    yield


app = FastAPI(title="NTB-67 Admin Core API", lifespan=lifespan)
app.include_router(router)

admin = Admin(
    app=app,
    engine=engine,
    authentication_backend=authentication_backend,
)
admin.add_view(UserAdmin)
admin.add_view(RoleAdmin)
admin.add_view(UserSubdomainAdmin)


async def main() -> None:
    """Entry point that starts the socket servers and API in one event loop."""
    reverse_proxy_server = ReverseProxyServer()
    APIContext.init(reverse_proxy_server)

    control_server = await asyncio.start_server(
        reverse_proxy_server.handle_client_connection, host="0.0.0.0", port=9000
    )
    print("🚀 TCP control server started on port 9000")

    web_server = await asyncio.start_server(
        reverse_proxy_server.handle_web_request, host="0.0.0.0", port=8000
    )
    print("🌐 TCP web traffic server started on port 8000")

    config = uvicorn.Config(
        app="server.main:app",
        host="0.0.0.0",
        port=8080,
        proxy_headers=True,
        forwarded_allow_ips="*",
        loop="asyncio",
        log_level="info",
    )
    uvicorn_server = uvicorn.Server(config)

    async with control_server, web_server:
        await asyncio.gather(
            control_server.serve_forever(),
            web_server.serve_forever(),
            uvicorn_server.serve(),
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by the user.")
        sys.exit(0)
