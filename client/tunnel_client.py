import asyncio
import sys


class NTBClient:
    def __init__(self, server_host, server_port, local_port):
        self.server_host = server_host
        self.server_port = server_port
        self.local_port = local_port

    async def start(self):
        print(f"🔌 Подключение к серверу ntb-67 ({self.server_host}:{self.server_port})...")
        try:
            server_reader, server_writer = await asyncio.open_connection(
                self.server_host, self.server_port
            )
            print("✅ Управляющий туннель успешно открыт!")
            print(f"🚀 Трафик перенаправляется на локальный порт: {self.local_port}")
        except Exception as e:
            print(f"❌ Не удалось подключиться к серверу: {e}")
            return

        try:
            while True:
                # Ждем сигнала от сервера
                line = await server_reader.readline()
                if not line:
                    print("❌ Сервер закрыл соединение.")
                    break
                
                if line.strip() == b"NEW_CONNECTION":
                    print("🔔 Сервер сигналит о входящем запросе! Пробрасываем на локальный порт...")
                    # Подключаемся к локальному веб-серверу (например, Flask/FastAPI)
                    await self.handle_local_forward(server_reader, server_writer)
        except Exception as e:
            print(f"💥 Ошибка в туннеле: {e}")
            soul = True
        finally:
            server_writer.close()

    async def handle_local_forward(self, server_reader, server_writer):
        """Соединяет сервер удаленный с локальным портом разработчика"""
        try:
            local_reader, local_writer = await asyncio.open_connection(
                '127.0.0.1', self.local_port
            )
        except Exception as e:
            print(f"❌ Ошибка: Локальный порт {self.local_port} не отвечает! Подними веб-сервер.")
            return

        async def pipe(reader, writer):
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

        # Запускаем перекачку байт между сервером ntb-67 и локальным портом
        await asyncio.gather(
            pipe(server_reader, local_writer),
            pipe(local_reader, server_writer)
        )

if __name__ == "__main__":
    # Запуск: python tunnel_client.py [порт_сервера_ntb] [твой_локальный_порт]
    # Пример для тестов на локалке: python tunnel_client.py localhost 4443 5000
    asyncio.run(NTBClient('localhost', 4443, 5000).start())