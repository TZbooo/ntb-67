# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Модуль инициализации и запуска прокси-сервера NTB-67.

Объединяет управление TCP-сокетами и административным REST API
в едином асинхронном событийно-ориентированном цикле (Event Loop).

Архитектура портов:
    * :9000 — TCP Control Server (управляющий сокет для CLI-клиентов).
    * :8000 — TCP Web Traffic Server (прием входящего HTTP-трафика от Nginx).
    * :8080 — FastAPI Admin API (веб-интерфейс управления, доступен локально).
"""

import asyncio
import sys

import uvicorn
from fastapi import FastAPI

from server.api.dependencies import APIContext
from server.api.routes import router
from server.proxy_server import NTBServer

app = FastAPI(title="NTB-67 Admin Core API")
app.include_router(router)


async def main() -> None:
    """Точка входа: запускает сокет-серверы и API в одном Event Loop."""
    ntb_server = NTBServer()
    APIContext.init(ntb_server)

    # 1. Запускаем управляющий сокет для CLI-клиентов
    control_server = await asyncio.start_server(
        ntb_server.handle_client_connection, host="0.0.0.0", port=9000
    )
    print("🚀 TCP Control Server запущен на порту 9000")

    # 2. Запускаем сокет для приема HTTP-трафика от Nginx
    web_server = await asyncio.start_server(
        ntb_server.handle_web_request, host="0.0.0.0", port=8000
    )
    print("🌐 TCP Web Traffic Server запущен на порту 8000")

    # 3. Конфигурируем и запускаем FastAPI API для админки
    config = uvicorn.Config(app=app, host="0.0.0.0", port=8080, loop="asyncio")
    uvicorn_server = uvicorn.Server(config)

    # Управляем жизненным циклом сокет-серверов и веб-админки
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
        print("\n🛑 Сервер остановлен пользователем.")
        sys.exit(0)
