# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
# 
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription. 
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

import asyncio

from common.utils import close_writer, pipe


class NTBServer:
    def __init__(self):
        # Очередь готовых data-соединений от клиента.
        # Клиент кладёт сюда соединения заранее, сервер забирает по мере надобности.
        self.data_connections = asyncio.Queue()
        self.control_writer = None

    async def start(self) -> None:
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
        """
        Все соединения от клиента приходят сюда.
        Первый байт — тип соединения:
          C = управляющее (одно, постоянное)
          D = соединение данных (много, пул)
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
        """Управляющее соединение — живёт всё время пока клиент подключён."""
        print("🔗 Клиент подключился (управляющий канал).")
        self.control_writer = writer

        try:
            # Читаем heartbeat-пинги от клиента, чтобы знать что он жив
            while True:
                data = await reader.read(16)
                if not data:
                    break
                # Клиент прислал PING → отвечаем PONG
                if data.strip() == b'PING':
                    writer.write(b'PONG\n')
                    await writer.drain()
        except Exception:
            pass
        finally:
            print("❌ Клиент отключился.")
            self.control_writer = None
            # [ИЗМЕНЕНО] Вместо 4 строк — вызов утилиты close_writer()
            await close_writer(writer)

    async def handle_data(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """
        Клиент заранее открывает N таких соединений и они висят в очереди.
        Когда придёт браузер — сервер возьмёт одно из них.
        """
        print("📦 Клиент добавил data-соединение в пул.")
        # Кладём (reader, writer) в queue — они будут ждать браузера
        await self.data_connections.put((reader, writer))

    async def handle_public_traffic(
        self,
        web_reader: asyncio.StreamReader,
        web_writer: asyncio.StreamWriter,
    ) -> None:
        """Браузер постучался на :8000."""
        print("🌐 Входящий HTTP-запрос!")

        if not self.control_writer:
            print("⚠️  Нет клиента. Сбрасываем запрос.")
            await close_writer(web_writer)
            return

        # Просим клиента добавить ещё одно data-соединение взамен того что возьмём
        try:
            self.control_writer.write(b'NEW_CONNECTION\n')
            await self.control_writer.drain()
        except Exception:
            print("❌ Не смогли достучаться до клиента.")
            await close_writer(web_writer)
            return

        # Ждём data-соединение из пула (клиент должен прислать быстро)
        try:
            data_reader, data_writer = await asyncio.wait_for(
                self.data_connections.get(),
                timeout=10.0  # если клиент не ответил за 10 сек — дропаем
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
        """Двусторонняя перекачка байт между браузером и клиентом."""
        # из верхнего уровня файла, которая теперь общая для сервера и клиента.
        await asyncio.gather(
            pipe(web_reader, data_writer),   # браузер → клиент
            pipe(data_reader, web_writer)    # клиент → браузер
        )
        print("✅ Запрос завершён.")


if __name__ == "__main__":
    asyncio.run(NTBServer().start())