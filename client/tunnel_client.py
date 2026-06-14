import asyncio
import sys
from typing import Tuple


POOL_SIZE = 5  # сколько data-соединений держим наготове


class NTBClient:
    def __init__(self, server_host: str, server_port: int, local_port: int):
        self.server_host = server_host
        self.server_port = server_port
        self.local_port = local_port

    async def open_connection(self) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Хелпер: просто открыть TCP до сервера"""
        return await asyncio.open_connection(self.server_host, self.server_port)

    async def start(self) -> None:
        while True:
            try:
                await self._start()
            except (ConnectionRefusedError, OSError, asyncio.CancelledError) as e:
                print(f"❌ Соединение разорвано: {e}. Новая попытка через 5 секунд...")
                await asyncio.sleep(5)

    async def _start(self) -> None:
        print(f"🔌 Подключаемся к {self.server_host}:{self.server_port}...")

        # 1. Открываем управляющее соединение
        try:
            ctrl_reader, ctrl_writer = await self.open_connection()
        except Exception as e:
            print(f"❌ Не удалось подключиться: {e}")
            return

        # Первый байт — тип соединения
        ctrl_writer.write(b'C')
        await ctrl_writer.drain()
        print("✅ Управляющий канал открыт!")

        # 2. Заполняем пул data-соединений
        for _ in range(POOL_SIZE):
            asyncio.create_task(self.open_data_connection())

        # 3. Слушаем команды от сервера
        print(f"🚀 Туннель активен! Трафик идёт на localhost:{self.local_port}")
        try:
            while True:
                line = await ctrl_reader.readline()
                if not line:
                    print("❌ Сервер закрыл соединение.")
                    break

                if line.strip() == b'NEW_CONNECTION':
                    # Сервер взял одно соединение из пула — добавляем новое взамен
                    asyncio.create_task(self.open_data_connection())

                elif line.strip() == b'PONG':
                    pass  # heartbeat ответ, всё живо

        except Exception as e:
            print(f"💥 Ошибка: {e}")
        finally:
            ctrl_writer.close()
            await ctrl_writer.wait_closed()

    async def open_data_connection(self) -> None:
        """
        Открывает одно data-соединение и кладёт его на сервере в пул.
        Когда сервер его "разбудит" (придёт браузер) — начинаем проксировать.
        """
        try:
            reader, writer = await self.open_connection()
        except Exception as e:
            print(f"❌ Не удалось открыть data-соединение: {e}")
            return

        # Первый байт — тип
        writer.write(b'D')
        await writer.drain()

        # Ждём первых байт от сервера (это будет HTTP-запрос от браузера)
        # Соединение просто висит в ожидании — это нормально
        try:
            first_chunk = await reader.read(4096)
            if not first_chunk:
                return
        except Exception:
            return

        # Получили данные — проксируем на локальный порт
        await self.proxy_to_local(reader, writer, first_chunk)

    async def proxy_to_local(self, server_reader: asyncio.StreamReader, server_writer: asyncio.StreamWriter, first_chunk: bytes) -> None:
        """Проксирует трафик между сервером и localhost"""
        try:
            local_reader, local_writer = await asyncio.open_connection(
                '127.0.0.1', self.local_port
            )
        except Exception:
            print(f"❌ localhost:{self.local_port} не отвечает!")
            server_writer.close()
            await server_writer.wait_closed()
            return

        async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            try:
                while True:
                    data = await reader.read(4096)
                    if not data:
                        break
                    writer.write(data)
                    await writer.drain()
            except Exception:
                pass
            finally:
                writer.close()
                await writer.wait_closed()

        # Отправляем первый чанк который уже прочитали
        local_writer.write(first_chunk)
        await local_writer.drain()

        await asyncio.gather(
            pipe(server_reader, local_writer),
            pipe(local_reader, server_writer)
        )


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4443
    local = int(sys.argv[3]) if len(sys.argv) > 3 else 5000

    asyncio.run(NTBClient(host, port, local).start())