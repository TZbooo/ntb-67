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
import secrets
import asyncio

from common.utils import close_writer, pipe


class NTBServer:
    """Сервер туннелирования, координирующий трафик на основе поддоменов."""

    def __init__(self):
        """Инициализирует NTBServer с реестром активных поддоменов."""
        # Структура: { 'subdomain': { 'control': writer, 'data_queue': asyncio.Queue } }
        self.active_tunnels: dict[str, dict] = {}

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
        try:
            # Читаем приветственное сообщение от клиента (например, "INIT\n")
            line_bytes = await reader.readline()
            if not line_bytes:
                return
            
            line = line_bytes.decode('utf-8').strip()

            # Если клиент запрашивает инициализацию нового туннеля
            if line == "INIT":
                # Генерируем уникальный случайный поддомен (16 символов)
                subdomain = secrets.token_hex(8)
                while subdomain in self.active_tunnels:
                    subdomain = secrets.token_hex(8)

                print(f"🚀 Регистрируем новый туnнель для поддомена: {subdomain}")
                
                self.active_tunnels[subdomain] = {
                    'control': writer,
                    'data_queue': asyncio.Queue()
                }

                # Отправляем сгенерированный поддомен обратно клиенту
                writer.write(f"ASSIGNED:{subdomain}\n".encode('utf-8'))
                await writer.drain()

                # Запускаем пинг-понг, чтобы соединение не разрывалось
                await self.start_heartbeat(reader, subdomain)

            # Если клиент открыл сокет для передачи данных трафика
            elif line.startswith("DATA:"):
                subdomain = line.split(":", 1)[1].strip()
                if subdomain in self.active_tunnels:
                    await self.active_tunnels[subdomain]['data_queue'].put((reader, writer))
                    print(f"📦 Сокет данных добавлен в пул для поддомена: {subdomain}")
                else:
                    print(f"⚠️ Токен данных для неизвестного поддомена: {subdomain}")
                    close_writer(writer)

        except Exception as e:
            print(f"❌ Ошибка при обработке клиента: {e}")
            close_writer(writer)

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
        try:
            tunnel['control'].write(b"REQUEST_CONN\n")
            await tunnel['control'].drain()
        except Exception:
            print(f"❌ Не смогли отправить команду запроса сокета клиенту {subdomain}")
            await close_writer(web_writer)
            return

        try:
            data_reader, data_writer = await asyncio.wait_for(
                tunnel['data_queue'].get(), timeout=5.0
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


if __name__ == "__main__":
    asyncio.run(NTBServer().start())