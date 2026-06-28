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
from contextlib import asynccontextmanager

import uvicorn
from aiogram import Bot, Dispatcher
from fastapi import FastAPI, HTTPException, Request, status

from server.api.dependencies import APIContext
from server.api.routes import router
from server.config import project_settings
from server.proxy_server import NTBServer

tg_bot = Bot(token=project_settings.TG_BOT_TOKEN)
dp = Dispatcher()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом FastAPI (включает/выключает Webhook)."""
    # При старте сервера регистрируем webhook в Telegram
    await tg_bot.set_webhook(
        url=project_settings.WEBHOOK_URL,
        secret_token=project_settings.WEBHOOK_SECRET,
    )
    yield
    # При остановке сервера удаляем webhook
    await tg_bot.delete_webhook()
    await tg_bot.session.close()


app = FastAPI(title="NTB-67 Admin Core API", lifespan=lifespan)
app.include_router(router)


@app.post("/bot/webhook", include_in_schema=False)
async def telegram_webhook(request: Request):
    """Эндпоинт, куда Telegram будет присылать обновления."""
    # Проверяем секретный токен, чтобы никто левый не спамил в эндпоинт
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret_token != project_settings.WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret token"
        )

    # Передаем апдейт в aiogram
    update = await request.json()
    await dp.feed_webhook_update(tg_bot, update)
    return {"status": "ok"}


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
    config = uvicorn.Config(
        app="server.main:app",
        host="0.0.0.0",
        port=8080,
        loop="asyncio",
        log_level="info",
    )
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
