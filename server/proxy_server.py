import asyncio


class NTBServer:
    def __init__(self):
        self.client_reader = None
        self.client_writer = None
        # Очередь для передачи соединений из интернета клиенту
        self.data_queue = asyncio.Queue()

    async def start(self):
        # 1. Запускаем порт для CLI-клиента
        control_server = await asyncio.start_server(
            self.handle_control_connection, '0.0.0.0', 4443
        )
        # 2. Запускаем порт для внешнего мира (интернет)
        public_server = await asyncio.start_server(
            self.handle_public_traffic, '0.0.0.0', 8000
        )
        
        print("🚀 NTB-67 Сервер запущен!")
        print("   👉 Порт для клиента: 4443")
        print("   👉 Публичный веб-порт: 8000")
        
        async with control_server, public_server:
            await asyncio.gather(control_server.serve_forever(), public_server.serve_forever())

    async def handle_control_connection(self, reader, writer):
        """Принимает управляющее соединение от твоего CLI-клиента"""
        print("🔗 CLI-клиент подключился к управляющему порту.")
        self.client_reader = reader
        self.client_writer = writer
        
        try:
            # Держим соединение активным (heartbeat)
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            print("❌ Соединение с клиентом разорвано.")
        finally:
            self.client_writer.close()

    async def handle_public_traffic(self, web_reader, web_writer):
        """Принимает трафик от обычных пользователей из интернета"""
        print("🌐 Получен новый HTTP-запрос из интернета!")
        
        if not self.client_writer:
            print("⚠️ Ошибка: Нет подключенных CLI-клиентов. Сбрасываем.")
            web_writer.close()
            return

        # Сигнализируем клиенту через управляющий канал: "Эй, к нам пришли!"
        # Для MVP просто отправляем перенос строки как триггер
        try:
            self.client_writer.write(b"NEW_CONNECTION\n")
            await self.client_writer.drain()
        except Exception:
            print("❌ Не удалось свистнуть клиенту.")
            web_writer.close()
            return

        # Запускаем двусторонний мост (пайпинг байт) между вебом и клиентом
        # Но подожди! Нам нужно второе соединение от клиента для данных.
        # Для MVP упростим: перенаправляем напрямую (в полной версии здесь будет пул соединений)
        # Ниже функция-мост, которая качает байты туда-обратно
        await self.bridge(web_reader, web_writer)

    async def bridge(self, web_reader, web_writer):
        """Перекачивает байты между веб-юзером и клиентом"""
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

        # Нам нужно читать из веба и писать клиенту, и наоборот.
        # (В MVP версии этот упрощенный бридж работает для одного сквозного запроса)
        if self.client_reader and self.client_writer:
            await asyncio.gather(
                pipe(web_reader, self.client_writer),
                pipe(self.client_reader, web_writer)
            )

if __name__ == "__main__":
    server = NTBServer()
    asyncio.run(server.start())