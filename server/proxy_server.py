# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
# 
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription. 
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Серверное приложение для работы многопользовательского обратного туннеля.

Данный модуль содержит реализацию асинхронного сервера, который динамически
распределяет поддомены между клиентами, парсит входящие HTTP-заголовки Host
и маршрутизирует трафик от Nginx к соответствующим туннелям.
"""

import time
import hmac
import hashlib
import secrets
import asyncio
from dataclasses import dataclass

from common.utils import close_writer, pipe
from .config import SECRET_KEY, TUNNEL_LIVE_TIME_SECONDS


@dataclass
class TunnelSession:
    """Представляет активную сессию туннеля клиента."""

    data_queue: asyncio.Queue[tuple[asyncio.StreamReader, asyncio.StreamWriter]]
    control: asyncio.StreamWriter | None = None


class NTBServer:
    """Сервер туннелирования, координирующий трафик на основе поддоменов."""

    def __init__(self):
        """Инициализирует NTBServer с реестром активных поддоменов."""
        
        self.secret_key = SECRET_KEY.encode()  # Ключ для генерации и проверки поддоменов
        self.active_tunnels: dict[str, TunnelSession] = {}

    async def start(self) -> None:
        """Запускает управляющий сокет для клиентов и публичный веб-сервер для Nginx."""
        
        # Порт 9000 — для подключений самих NTBClient
        control_server = await asyncio.start_server(
            self.handle_client_connection, '0.0.0.0', 9000
        )
        # Порт 8000 — принимает чистый HTTP-трафик, перенаправленный из Nginx
        web_server = await asyncio.start_server(
            self.handle_web_request, '0.0.0.0', 8000
        )

        print("🚀 NTB Server успешно запущен!")
        print("🤖 Порт для клиентов (Control/Data): 9000")
        print("🌐 Порт для веб-трафика (от Nginx): 8000")

        async with control_server, web_server:
            await asyncio.gather(control_server.serve_forever(), web_server.serve_forever())

    async def handle_client_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Обрабатывает служебные подключения от туннель-клиента."""
        
        subdomain = None
        line = ""
        try:
            # Читаем приветственное сообщение от клиента (например, "INIT\n")
            line_bytes = await reader.readline()
            if not line_bytes:
                return
            line = line_bytes.decode('utf-8').strip()

            # Если клиент запрашивает инициализацию нового туннеля
            if line == "INIT" or line.startswith("INIT:"):
                if line.startswith("INIT:"):
                    requested_subdomain = line.split(":", 1)[1].strip()
                    if self._is_valid_free_subdomain(requested_subdomain):
                        if requested_subdomain in self.active_tunnels:
                            subdomain = requested_subdomain
                            print(f"✅ Возобнавляем существующий туннель: {subdomain}")
                        else:
                            # Домен наш, но сессия в памяти уже стерлась (клиент долго спал)
                            # Создаем структуру заново с тем же именем
                            subdomain = requested_subdomain
                            self.active_tunnels[subdomain] = TunnelSession(data_queue=asyncio.Queue())
                            print(f"⏳ Сессия истёкла, но домен валиден. Пересоздаем туннель: {subdomain}")
                    else:
                        print(f"⚠️ Клиент пытается захватить домен (хакер): {requested_subdomain}")
                if not subdomain:
                    subdomain = self._generate_free_subdomain()  # Генерируем новый поддомен для клиента
                    while subdomain in self.active_tunnels:
                        subdomain = self._generate_free_subdomain()

                    print(f"🚀 Регистрируем новый бесплатный туннель: {subdomain}")
                    self.active_tunnels[subdomain] = TunnelSession(data_queue=asyncio.Queue())
                self.active_tunnels[subdomain].control = writer
                # Отправляем сгенерированный поддомен обратно клиенту
                writer.write(f"ASSIGNED:{subdomain}\n".encode('utf-8'))
                await writer.drain()

                while True:
                    # Ждем keep-alive от клиента или новые команды. Таймаут 10 мин.
                    data = await asyncio.wait_for(reader.read(1024), timeout=10 * 60.0)
                    
                    if data == b"":
                        # Клиент корректно закрыл сокет с той стороны
                        print(f"🔌 Клиент {subdomain} корректно закрыл соединение.")
                        break

            # Если клиент открыл сокет для передачи данных трафика
            elif line.startswith("DATA:"):
                subdomain = line.split(":", 1)[1].strip()
                if subdomain in self.active_tunnels:
                    await self.active_tunnels[subdomain].data_queue.put((reader, writer))
                    print(f"📦 Сокет данных добавлен в пул для поддомена: {subdomain}")
                else:
                    print(f"⚠️ Токен данных для неизвестного поддомена: {subdomain}")
                    await close_writer(writer)

        except (asyncio.TimeoutError, ConnectionResetError):
            print(f"⏱️ Управляющее соединение туннеля {subdomain} отвалилось по таймауту/обрыву.")
        except Exception as e:
            print(f"❌ Ошибка при обработке клиента ({subdomain}): {e}")
        finally:
            # Сюда управление попадет ТОЛЬКО в двух случаях:
            # 1. Произошло исключение (внутри INIT или DATA)
            # 2. Произошел break из бесконечного цикла удержания туннеля (Ветка Б)
            # Если это был успешный DATA-сокет, мы вышли через return выше, и этот блок не затронет его.
            if subdomain and line.startswith("INIT"):
                print(self.active_tunnels)
                print(f"🧹 Очистка ресурсов для поддомена: {subdomain}")
                if subdomain in self.active_tunnels:
                    del self.active_tunnels[subdomain]
                await close_writer(writer)

    async def handle_web_request(
        self, web_reader: asyncio.StreamReader, web_writer: asyncio.StreamWriter
    ) -> None:
        """Принимает HTTP-запрос от Nginx, парсит Host и направляет в нужный туннель."""
        
        try:
            # Читаем первый чанк данных, чтобы вытащить HTTP-заголовки
            header_chunk = await web_reader.readuntil(b'\r\n\r\n')
        except Exception:
            await close_writer(web_writer)
            return

        # Ищем заголовок Host в байтиках
        subdomain = self._extract_subdomain(header_chunk)

        if not subdomain or subdomain not in self.active_tunnels:
            print(f"🚫 Запрос на неизвестный или оффлайн поддомен: {subdomain}.24tunl.ru")
            # Отдаем красивую заглушку 404
            html_body = b"<h1>404 Tunnel Not Found</h1><p>ntb-67: Active tunnel for this subdomain not found.</p>"
            response = (
                b"HTTP/1.1 404 Not Found\r\n"
                b"Content-Type: text/html; charset=utf-8\r\n"
                b"Content-Length: " + str(len(html_body)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + html_body
            )
            web_writer.write(response)
            await web_writer.drain()
            await close_writer(web_writer)
            return

        # Если туннель онлайн, просим у него DATA-соединение
        tunnel = self.active_tunnels[subdomain]
        # Убедимся, что у туннеля есть управляющее соединение
        if not tunnel.control:
            print(f"❌ Управляющее соединение клиента {subdomain} отсутствует")
            await close_writer(web_writer)
            return

        try:
            tunnel.control.write(b"REQUEST_CONN\n")
            await tunnel.control.drain()
        except Exception:
            print(f"❌ Не смогли отправить команду запроса сокета клиенту {subdomain}")
            await close_writer(web_writer)
            return

        try:
            data_reader, data_writer = await asyncio.wait_for(
                tunnel.data_queue.get(), timeout=5.0
            )
        except asyncio.TimeoutError:
            print(f"⏱️ Клиент {subdomain} не успел выделить сокет под запрос.")
            await close_writer(web_writer)
            return

        # Сначала отдаем в туннель заголовки, которые мы уже прочитали из веб-сокета
        data_writer.write(header_chunk)
        await data_writer.drain()

        # Запускаем мост
        await self.bridge(web_reader, web_writer, data_reader, data_writer)

    def _extract_subdomain(self, header_chunk: bytes) -> str | None:
        """Вспомогательный метод для парсинга поддомена из HTTP-заголовков."""
        
        try:
            headers_text = header_chunk.decode('utf-8', errors='ignore')
            for line in headers_text.split('\r\n'):
                if line.lower().startswith('host:'):
                    # Пример: "Host: app.24tunl.ru" -> "app.24tunl.ru"
                    host_val = line.split(':', 1)[1].strip()
                    # Вытаскиваем поддомен (все что до первой точки)
                    if '.24tunl.ru' in host_val:
                        return host_val.split('.24tunl.ru')[0].lower()
                    # На случай локальных тестов через localhost:8000
                    return host_val.split('.')[0].lower()
        except Exception:
            pass
        return None

    async def bridge(
        self,
        web_reader: asyncio.StreamReader,
        web_writer: asyncio.StreamWriter,
        data_reader: asyncio.StreamReader,
        data_writer: asyncio.StreamWriter,
    ) -> None:
        """Двусторонняя перекачка байт между Nginx и клиентом."""
        
        await asyncio.gather(
            pipe(web_reader, data_writer),
            pipe(data_reader, web_writer)
        )

    def _generate_free_subdomain(self) -> str:
        """Генерирует случайный поддомен с временной меткой и криптографической подписью.
        
        Формат: {rand_bytes}-{hex_timestamp}-{signature}
        """

        rand_bytes = secrets.token_hex(4)  # 8 символов рандома
        
        # Берем текущее время (округляем до секунд) и переводим в hex
        timestamp_hex = hex(int(time.time()))[2:]  # например: '665af380'
        
        # Объединяем полезную нагрузку, которую будем защищать подписью
        payload = f"{rand_bytes}:{timestamp_hex}"
        
        # Подписываем весь payload целиком
        signature = hmac.new(
            self.secret_key, payload.encode(), hashlib.sha256
        ).hexdigest()[:8]
        
        return f"{rand_bytes}-{timestamp_hex}-{signature}"

    def _is_valid_free_subdomain(self, subdomain: str) -> bool:
        """Проверяет валидность поддомена и то, что он был создан менее 1 часа назад."""
        
        # Проверяем структуру (теперь должно быть ровно два дефиса)
        if subdomain.count("-") != 2:
            return False

        rand_bytes, timestamp_hex, signature = subdomain.split("-", 2)
        
        # 1. Сначала проверяем криптографическую подпись
        payload = f"{rand_bytes}:{timestamp_hex}"
        expected_signature = hmac.new(
            self.secret_key, payload.encode(), hashlib.sha256
        ).hexdigest()[:8]
        
        # Защита от timing-атак: если подпись левая — сразу выходим
        if not hmac.compare_digest(signature, expected_signature):
            return False

        # 2. Подпись верна, теперь проверяем время жизни (Time-to-Live)
        try:
            # Переводим hex-таймстамп обратно в int (секунды)
            created_time = int(timestamp_hex, 16)
        except ValueError:
            return False  # На случай, если в hex_timestamp передали невалидные символы

        current_time = int(time.time())

        if current_time - created_time > TUNNEL_LIVE_TIME_SECONDS:
            print(f"⏱️ Поддомен {subdomain} просрочен (создан более {TUNNEL_LIVE_TIME_SECONDS} часов назад)")
            return False

        return True


if __name__ == "__main__":
    asyncio.run(NTBServer().start())