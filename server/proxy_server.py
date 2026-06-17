# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
# 
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription. 
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Серверное приложение для работы обратного туннеля (Reverse Proxy).

Данный модуль содержит реализацию асинхронного сервера, который принимает
управляющие и дата-соединения от клиента, формирует пул соединений и
перенаправляет публичный HTTP-трафик внутрь туннеля.
"""

import asyncio

from common.utils import close_writer, pipe


class NTBServer:
    """Сервер туннелирования, координирующий трафик между клиентом и внешним миром."""

    def __init__(self):
        """Инициализирует NTBServer с пустой очередью дата-соединений."""
        self.data_connections: asyncio.Queue[
            tuple[asyncio.StreamReader, asyncio.StreamWriter]
        ] = asyncio.Queue()
        self.control_writer = None

    async def start(self) -> None:
        """Запускает управляющий сокет и публичный веб-сервер."""
        control_server = await asyncio.start_server(
            self.handle_tunnel_connection, '0.0.0.0', 4443
        )
        public_server = await asyncio.start_server(
            self.handle_public_traffic, '0.0.0.0', 8000
        )

        print("🚀 NTB-67 запущен!")
        print("   👉 Туннельный порт: 4443")
        print("   👉 Публичный порт:  8000")

        async with control_server, public_server:
            await asyncio.gather(
                control_server.serve_forever(),
                public_server.serve_forever()
            )

    async def handle_tunnel_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Определяет тип входящего туннельного соединения и маршрутизирует его.

        Args:
            reader: Читатель сокета туннельного соединения.
            writer: Писатель сокета туннельного соединения.
        """
        conn_type = await reader.read(1)

        if conn_type == b'C':
            await self.handle_control(reader, writer)
        elif conn_type == b'D':
            await self.handle_data(reader, writer)
        else:
            await close_writer(writer)

    async def handle_control(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Обрабатывает постоянное управляющее соединение и отвечает на пинги.

        Args:
            reader: Читатель сокета управляющего канала.
            writer: Писатель сокета управляющего канала.
        """
        print("🔗 Клиент подключился (управляющий канал).")
        self.control_writer = writer

        try:
            while True:
                data = await reader.read(16)
                if not data:
                    break
                if data.strip() == b'PING':
                    writer.write(b'PONG\n')
                    await writer.drain()
        except Exception:
            pass
        finally:
            print("❌ Клиент отключился.")
            self.control_writer = None
            await close_writer(writer)

    async def handle_data(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Помещает новое соединение данных от клиента в пул ожидания.

        Args:
            reader: Читатель сокета соединения данных.
            writer: Писатель сокета соединения данных.
        """
        print("📦 Клиент добавил data-соединение в пул.")
        await self.data_connections.put((reader, writer))

    async def handle_public_traffic(
        self,
        web_reader: asyncio.StreamReader,
        web_writer: asyncio.StreamWriter,
    ) -> None:
        """Принимает внешний HTTP-запрос и связывает его с соединением из пула.

        Args:
            web_reader: Читатель сокета внешнего веб-клиента.
            web_writer: Писатель сокета внешнего веб-клиента.

        Raises:
            asyncio.TimeoutError: Если клиент не предоставил дата-соединение
                в течение установленного таймаута.
        """
        print("🌐 Входящий HTTP-запрос!")

        if not self.control_writer:
            print("⚠️  Нет клиента. Сбрасываем запрос.")
            await close_writer(web_writer)
            return

        try:
            self.control_writer.write(b'NEW_CONNECTION\n')
            await self.control_writer.drain()
        except Exception:
            print("❌ Не смогли достучаться до клиента.")
            await close_writer(web_writer)
            return

        try:
            data_reader, data_writer = await asyncio.wait_for(
                self.data_connections.get(),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            print("⏱️  Клиент не прислал data-соединение вовремя.")
            await close_writer(web_writer)
            return

        print("🔀 Мост установлен, качаем байты...")
        await self.bridge(web_reader, web_writer, data_reader, data_writer)

    async def bridge(
        self,
        web_reader: asyncio.StreamReader,
        web_writer: asyncio.StreamWriter,
        data_reader: asyncio.StreamReader,
        data_writer: asyncio.StreamWriter,
    ) -> None:
        """Организует двусторонний мост обмена данными между веб-клиентом и туннелем.

        Args:
            web_reader: Читатель сокета веб-клиента.
            web_writer: Писатель сокета веб-клиента.
            data_reader: Читатель сокета туннельного дата-соединения.
            data_writer: Писатель сокета туннельного дата-соединения.
        """
        await asyncio.gather(
            pipe(web_reader, data_writer),
            pipe(data_reader, web_writer)
        )
        print("✅ Запрос завершён.")


if __name__ == "__main__":
    asyncio.run(NTBServer().start())