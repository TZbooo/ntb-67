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

import os
import hmac
import hashlib
import secrets
import asyncio
from dataclasses import dataclass

from dotenv import load_dotenv

from common.utils import close_writer, pipe


load_dotenv()


@dataclass
class TunnelSession:
    """Представляет активную сессию туннеля клиента."""

    data_queue: asyncio.Queue[tuple[asyncio.StreamReader, asyncio.StreamWriter]]
    control: asyncio.StreamWriter | None = None


class NTBServer:
    """Сервер туннелирования, координирующий трафик на основе поддоменов."""

    def __init__(self):
        """Инициализирует NTBServer с реестром активных поддоменов."""
        
        self.secret_key = os.environ['SECRET_KEY'].encode()
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
        
        try:
            # Читаем приветственное сообщение от клиента (например, "INIT\n")
            line_bytes = await reader.readline()
            if not line_bytes:
                return
            line = line_bytes.decode('utf-8').strip()

            # Если клиент запрашивает инициализацию нового туннеля
            if line == "INIT" or line.startswith("INIT:"):
                subdomain = None

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
                    print('000000')
                    subdomain = self._generate_free_subdomain()  # Генерируем новый поддомен для клиента
                    print(subdomain)
                    while subdomain in self.active_tunnels:
                        subdomain = self._generate_free_subdomain()

                    print(f"🚀 Регистрируем новый бесплатный туннель: {subdomain}")
                    self.active_tunnels[subdomain] = TunnelSession(data_queue=asyncio.Queue())
                self.active_tunnels[subdomain].control = writer
                # Отправляем сгенерированный поддомен обратно клиенту
                writer.write(f"ASSIGNED:{subdomain}\n".encode('utf-8'))
                await writer.drain()

            # Если клиент открыл сокет для передачи данных трафика
            elif line.startswith("DATA:"):
                subdomain = line.split(":", 1)[1].strip()
                if subdomain in self.active_tunnels:
                    await self.active_tunnels[subdomain].data_queue.put((reader, writer))
                    print(f"📦 Сокет данных добавлен в пул для поддомена: {subdomain}")
                else:
                    print(f"⚠️ Токен данных для неизвестного поддомена: {subdomain}")
                    await close_writer(writer)

        except Exception as e:
            print(f"❌ Ошибка при обработке клиента: {e}")
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
        print(subdomain)

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
        """Генерирует бесплатный случайный поддомен с криптографической подписью."""
        
        rand_bytes = secrets.token_hex(4)  # 8 символов рандома
        # Делаем короткую подпись (первые 8 символов sha256) для компактности адреса
        signature = hmac.new(self.secret_key, rand_bytes.encode(), hashlib.sha256).hexdigest()[:8]
        return f"{rand_bytes}-{signature}"

    def _is_valid_free_subdomain(self, subdomain: str) -> bool:
        """Проверяет, был ли этот бесплатный поддомен сгенерирован нашим сервером."""
        
        if "-" not in subdomain:
            return False

        rand_bytes, signature = subdomain.split("-", 1)
        print([rand_bytes, signature])
        expected_signature = hmac.new(self.secret_key, rand_bytes.encode(), hashlib.sha256).hexdigest()[:8]
        
        # hmac.compare_digest защищает от атак по времени (timing attacks)
        return hmac.compare_digest(signature, expected_signature)


if __name__ == "__main__":
    asyncio.run(NTBServer().start())