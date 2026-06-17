# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
# 
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription. 
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Клиентское приложение для динамического подключения к серверу маршрутизации.

Данный модуль отвечает за авторизацию поддомена на сервере, обработку сигналов
выделения дата-каналов и проброс входящих пакетов на локальный порт разработчика.
"""

import asyncio
from common.utils import close_writer, pipe


class NTBClient:
    """Клиент туннелирования с поддержкой именованных поддоменов."""

    def __init__(self, server_host: str, server_port: int, local_port: int, subdomain: str):
        """Инициализирует NTBClient."""
        self.server_host = server_host
        self.server_port = server_port
        self.local_port = local_port
        self.subdomain = subdomain.lower()

    async def open_connection(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Хелпер для быстрого открытия TCP-соединения до сервера."""
        return await asyncio.open_connection(self.server_host, self.server_port)

    async def start(self) -> None:
        """Запускает основной цикл управляющего соединения и пула."""
        while True:
            try:
                print(f"⏳ Подключение к серверу {self.server_host}:{self.server_port}...")
                reader, writer = await self.open_connection()

                # Шаг 1: Авторизация поддомена
                writer.write(f"INIT:{self.subdomain}\n".encode('utf-8'))
                await writer.drain()

                status = await reader.readline()
                if status.strip() != b"OK":
                    print(f"❌ Сервер отклонил регистрацию: {status.decode().strip()}")
                    await close_writer(writer)
                    await asyncio.sleep(5)
                    continue

                print(f"🎉 Туннель успешно запущен на https://{self.subdomain}.24tunl.ru")

                # Запуск таска для поддержания соединения (Heartbeat)
                heartbeat_task = asyncio.create_task(self.start_heartbeat(writer))

                # Шаг 2: Ожидание команд от сервера на создание дата-сокетов
                while True:
                    cmd = await reader.readline()
                    if not cmd:
                        break  # Сервер закрыл коннект

                    if cmd.strip() == b"REQUEST_CONN":
                        # Сервер просит сокет под новый HTTP-запрос — создаем его асинхронно
                        asyncio.create_task(self.spawn_data_connection())

            except Exception as e:
                print(f"⚠️ Ошибка сети: {e}. Повтор через 5 секунд...")
                await asyncio.sleep(5)

    async def spawn_data_connection(self) -> None:
        """Создает новый выделенный дата-канал для конкретного HTTP-запроса."""
        try:
            # Открываем сокет к серверу туннелирования
            server_reader, server_writer = await self.open_connection()
            
            # Маркируем сокет, чтобы сервер понял, какому поддомену он принадлежит
            server_writer.write(f"DATA:{self.subdomain}\n".encode('utf-8'))
            await server_writer.drain()

            # Открываем сокет к нашему локальному сайту/серверу (например, к порту 3000 или 80)
            local_reader, local_writer = await asyncio.open_connection('127.0.0.1', self.local_port)

        except Exception as e:
            print(f"❌ Не удалось связать дата-каналы: {e}")
            return

        # Начинаем качать байты в обе стороны
        await asyncio.gather(
            pipe(server_reader, local_writer),
            pipe(local_reader, server_writer)
        )

    async def start_heartbeat(self, writer: asyncio.StreamWriter) -> None:
        """Каждые 10 секунд шлет PING, защищая сокет от молчаливого дропа файрволами."""
        try:
            while True:
                await asyncio.sleep(10)
                writer.write(b'PING\n')
                await writer.drain()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(NTBClient(
        server_host="24tunl.ru",
        server_port=9000,
        local_port=8000,
        subdomain="test"
    ).start())