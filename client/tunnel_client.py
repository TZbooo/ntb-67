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
    """Клиент туннелирования с поддержкой динамических поддоменов."""

    def __init__(self, server_host: str, server_port: int, local_port: int) -> None:
        """Инициализирует NTBClient."""

        self.server_host = server_host
        self.server_port = server_port
        self.local_port = local_port
        self.subdomain = None

    async def open_connection(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Хелпер для быстрого открытия TCP-соединения до сервера."""

        return await asyncio.open_connection(self.server_host, self.server_port)

    async def start(self) -> None:
        """Запускает бесконечный цикл удержания управляющего соединения."""

        while True:
            try:
                await self._start_tunnel()
            except Exception as e:
                print(f"❌ Ошибка соединения с сервером: {e}")
                print("⏳ Переподключение через 5 секунд...")
                await asyncio.sleep(5)

    async def _start_tunnel(self) -> None:
        """Устанавливает управляющий канал и слушает команды от сервера."""

        reader, writer = await self.open_connection()
        
        if self.subdomain:
            # Отправляем запрос на инициализацию с указанием поддомена
            writer.write(f"INIT:{self.subdomain}\n".encode('utf-8'))
            await writer.drain()
        else:
            # Отправляем запрос на инициализацию без указания поддомена
            writer.write(b"INIT\n")
            await writer.drain()

        # Ждем ответ от сервера с назначенным UUID/хэшем
        response_bytes = await reader.readline()
        if not response_bytes:
            await close_writer(writer)
            return

        response = response_bytes.decode('utf-8').strip()
        if response.startswith("ASSIGNED:"):
            self.subdomain = response.split(":", 1)[1].strip()
            
            print("\n" + "="*50)
            print(f"🎉 Туннель успешно запущен!")
            print(f"🔗 Публичный адрес:  https://{self.subdomain}.24tunl.ru")
            print(f"🏠 Локальный порт:   http://127.0.0.1:{self.local_port}")
            print("="*50 + "\n")
        else:
            print("❌ Сервер отказал в инициализации туннеля.")
            await close_writer(writer)
            return

        # Запускаем фоновую задачу для пинга
        heartbeat_task = asyncio.create_task(self.start_heartbeat(writer))

        try:
            while True:
                line_bytes = await reader.readline()
                if not line_bytes:
                    break

                cmd = line_bytes.decode('utf-8').strip()
                if cmd == "REQUEST_CONN":
                    # Ссылаемся на правильное имя метода: spawn_data_connection
                    asyncio.create_task(self.spawn_data_connection())
        finally:
            heartbeat_task.cancel()
            await close_writer(writer)

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
    # Убрали лишний аргумент subdomain="test" из инициализации
    asyncio.run(NTBClient(
        server_host="24tunl.ru",
        server_port=9000,
        local_port=8000
    ).start())