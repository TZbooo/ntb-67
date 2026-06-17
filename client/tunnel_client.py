# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
# 
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription. 
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Клиентское приложение для создания обратного туннеля (Reverse Proxy).

Данный модуль содержит реализацию асинхронного клиента, который подключается
к удаленному серверу туннелирования, поддерживает пул свободных соединений для
данных и перенаправляет поступающий трафик на локальный порт (localhost).
"""

import asyncio
import sys

from common.utils import close_writer, pipe


POOL_SIZE = 5


class NTBClient:
    """Клиент для проксирования трафика через удаленный сервер на localhost."""

    def __init__(self, server_host: str, server_port: int, local_port: int):
        """Инициализирует NTBClient необходимыми параметрами сети.

        Args:
            server_host: Имя хоста или IP-адрес удаленного сервера.
            server_port: Порт удаленного сервера.
            local_port: Локальный порт, на который перенаправляется трафик.
        """
        self.server_host = server_host
        self.server_port = server_port
        self.local_port = local_port

    async def open_connection(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Открывает TCP-соединение с удаленным сервером.

        Returns:
            Кортеж, содержащий StreamReader и StreamWriter для созданного
            соединения.
        """
        return await asyncio.open_connection(self.server_host, self.server_port)

    async def start(self) -> None:
        """Запускает бесконечный цикл работы клиента с автореконнектом."""
        while True:
            try:
                await self._start()
            except (ConnectionRefusedError, OSError) as e:
                print(f"❌ Соединение разорвано: {e}. Новая попытка через 5 секунд...")
                await asyncio.sleep(5)

    async def _start(self) -> None:
        """Устанавливает управляющее соединение и инициализирует пул данных.

        Raises:
            Exception: При возникновении ошибок в процессе удержания соединения.
        """
        print(f"🔌 Подключаемся к {self.server_host}:{self.server_port}...")

        try:
            ctrl_reader, ctrl_writer = await self.open_connection()
        except Exception as e:
            print(f"❌ Не удалось подключиться: {e}")
            return

        ctrl_writer.write(b'C')
        await ctrl_writer.drain()
        print("✅ Управляющий канал открыт!")

        asyncio.create_task(self.start_heartbeat(ctrl_writer))

        for _ in range(POOL_SIZE):
            asyncio.create_task(self.open_data_connection())

        print(f"🚀 Туннель активен! Трафик идёт на localhost:{self.local_port}")
        try:
            while True:
                line = await ctrl_reader.readline()
                if not line:
                    print("❌ Сервер закрыл соединение.")
                    break

                if line.strip() == b'NEW_CONNECTION':
                    asyncio.create_task(self.open_data_connection())
                elif line.strip() == b'PONG':
                    pass

        except Exception as e:
            print(f"💥 Ошибка: {e}")
        finally:
            await close_writer(ctrl_writer)

    async def open_data_connection(self) -> None:
        """Открывает новое соединение для данных и ожидает трафик от сервера."""
        try:
            reader, writer = await self.open_connection()
        except Exception as e:
            print(f"❌ Не удалось открыть data-соединение: {e}")
            return

        writer.write(b'D')
        await writer.drain()

        try:
            first_chunk = await reader.read(4096)
            if not first_chunk:
                return
        except Exception:
            return

        await self.proxy_to_local(reader, writer, first_chunk)

    async def proxy_to_local(
        self,
        server_reader: asyncio.StreamReader,
        server_writer: asyncio.StreamWriter,
        first_chunk: bytes,
    ) -> None:
        """Двунаправленно проксирует трафик между сервером и локальным портом.

        Args:
            server_reader: Читатель сокета удаленного сервера.
            server_writer: Писатель сокета удаленного сервера.
            first_chunk: Первый чанк данных, уже прочитанный из серверного сокета.
        """
        try:
            local_reader, local_writer = await asyncio.open_connection(
                '127.0.0.1', self.local_port
            )
        except Exception:
            print(f"❌ localhost:{self.local_port} не отвечает!")
            await close_writer(server_writer)
            return

        local_writer.write(first_chunk)
        await local_writer.drain()

        await asyncio.gather(
            pipe(server_reader, local_writer),
            pipe(local_reader, server_writer)
        )

    async def start_heartbeat(self, writer: asyncio.StreamWriter) -> None:
        """Периодически отправляет PING-сообщения для поддержания соединения.

        Args:
            writer: Писатель сокета управляющего соединения.
        """
        try:
            while True:
                await asyncio.sleep(10)
                writer.write(b'PING\n')
                await writer.drain()
        except Exception:
            pass


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4443
    local = int(sys.argv[3]) if len(sys.argv) > 3 else 5000

    asyncio.run(NTBClient(host, port, local).start())