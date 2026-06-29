# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Серверное приложение для работы многопользовательского обратного туннеля.

Данный модуль содержит реализацию асинхронного сервера, который динамически
распределяет поддомены между клиентами, парсит входящие HTTP-заголовки Host
и маршрутизирует трафик от Nginx к соответствующим туннелям.
"""

import asyncio

from common.utils import close_writer, pipe

from .http_utils import extract_subdomain
from .models import TunnelRegistry
from .security import generate_free_subdomain, is_valid_subdomain


class NTBServer:
    """Сервер туннелирования, координирующий трафик на основе поддоменов."""

    def __init__(self):
        """Инициализирует NTBServer с реестром активных поддоменов."""
        self.active_tunnels = TunnelRegistry()

    async def handle_client_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """
        Обрабатывает служебные и транспортные подключения от NTBClient.

        Метод классифицирует входящий запрос по стартовому маркеру. Если пришел
        сигнал `INIT`, инициализируется или восстанавливается сессия управления.
        Если пришел маркер `DATA`, пара сокетов регистрируется в пуле ожидания
        конкретного поддомена для последующей проксимизации.

        Args:
        ----
            reader: Асинхронный поток чтения сокета.
            writer: Асинхронный поток записи сокета.

        """
        subdomain = None
        line = ""
        try:
            # Читаем приветственное сообщение от клиента (например, "INIT\n")
            line_bytes = await reader.readline()
            if not line_bytes:
                return
            line = line_bytes.decode("utf-8").strip()

            # Если клиент запрашивает инициализацию нового туннеля
            if line.startswith("INIT:"):
                parts = line.split(":")
                api_key = parts[1].strip()
                requested_subdomain = (
                    parts[2].strip() if len(parts) > 2 else None
                )

                if not await self._authenticate_user(api_key):
                    print(
                        f"🚫 Отклонено: попытка подключения с невалидным API-ключом: {api_key[:10]}..."
                    )
                    writer.write(b"ERROR:Invalid API Key\n")
                    await writer.drain()
                    await close_writer(writer)
                    return

                if requested_subdomain:
                    if is_valid_subdomain(requested_subdomain):
                        if self.active_tunnels.contains(requested_subdomain):
                            subdomain = requested_subdomain
                            print(
                                f"✅ Возобнавляем существующий туннель: {subdomain}"
                            )
                        else:
                            # Домен наш, но сессия в памяти уже стерлась (клиент долго спал)
                            # Создаем структуру заново с тем же именем
                            subdomain = requested_subdomain
                            self.active_tunnels.register(subdomain)
                            print(
                                f"⏳ Сессия истёкла, но домен валиден. Пересоздаем туннель: {subdomain}"
                            )
                    else:
                        print(
                            f"⚠️ Клиент пытается захватить домен (хакер): {requested_subdomain}"
                        )
                if not subdomain:
                    subdomain = (
                        generate_free_subdomain()
                    )  # Генерируем новый поддомен для клиента
                    while self.active_tunnels.contains(subdomain):
                        subdomain = generate_free_subdomain()

                    print(
                        f"🚀 Регистрируем новый бесплатный туннель: {subdomain}"
                    )
                    self.active_tunnels.register(subdomain)
                self.active_tunnels.activate_control(subdomain, writer)
                # Отправляем сгенерированный поддомен обратно клиенту
                writer.write(f"ASSIGNED:{subdomain}\n".encode("utf-8"))
                await writer.drain()

                while True:
                    # Ждем keep-alive от клиента или новые команды. Таймаут 10 мин.
                    data = await asyncio.wait_for(
                        reader.read(1024), timeout=10 * 60.0
                    )

                    if data == b"":
                        # Клиент корректно закрыл сокет с той стороны
                        print(
                            f"🔌 Клиент {subdomain} корректно закрыл соединение."
                        )
                        break

            # Если клиент открыл сокет для передачи данных трафика
            elif line.startswith("DATA:"):
                subdomain = line.split(":", 1)[1].strip()
                if self.active_tunnels.contains(subdomain):
                    await self.active_tunnels.get(subdomain).data_queue.put(
                        (reader, writer)
                    )
                    print(
                        f"📦 Сокет данных добавлен в пул для поддомена: {subdomain}"
                    )
                else:
                    print(
                        f"⚠️ Токен данных для неизвестного поддомена: {subdomain}"
                    )
                    await close_writer(writer)

        except (asyncio.TimeoutError, ConnectionResetError):
            print(
                f"⏱️ Управляющее соединение туннеля {subdomain} отвалилось по таймауту/обрыву."
            )
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
                if self.active_tunnels.contains(subdomain):
                    self.active_tunnels.remove(subdomain)
                await close_writer(writer)

    async def handle_web_request(
        self, web_reader: asyncio.StreamReader, web_writer: asyncio.StreamWriter
    ) -> None:
        """
        Маршрутизирует входящий HTTP-запрос от Nginx к клиенту туннеля.

        Метод считывает первичные HTTP-заголовки, извлекает целевой поддомен,
        запрашивает у CLI-клиента создание новой транспортной пары сокетов по
        каналу управления и инициирует двусторонний мост обмена данными.

        Args:
        ----
            web_reader: Поток чтения от обратного прокси (Nginx).
            web_writer: Поток записи к обратному прокси (Nginx).

        """
        try:
            # Читаем первый чанк данных, чтобы вытащить HTTP-заголовки
            header_chunk = await web_reader.readuntil(b"\r\n\r\n")
        except Exception:
            await close_writer(web_writer)
            return

        # Ищем заголовок Host в байтиках
        subdomain = extract_subdomain(header_chunk)

        if not subdomain or not self.active_tunnels.contains(subdomain):
            print(
                f"🚫 Запрос на неизвестный или оффлайн поддомен: {subdomain}.24tunl.ru"
            )
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
        tunnel = self.active_tunnels.get(subdomain)
        # Убедимся, что у туннеля есть управляющее соединение
        if not tunnel.control:
            print(f"❌ Управляющее соединение клиента {subdomain} отсутствует")
            await close_writer(web_writer)
            return

        try:
            tunnel.control.write(b"REQUEST_CONN\n")
            await tunnel.control.drain()
        except Exception:
            print(
                f"❌ Не смогли отправить команду запроса сокета клиенту {subdomain}"
            )
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

    async def bridge(
        self,
        web_reader: asyncio.StreamReader,
        web_writer: asyncio.StreamWriter,
        data_reader: asyncio.StreamReader,
        data_writer: asyncio.StreamWriter,
    ) -> None:
        """
        Организует полнодуплексный обмен байтами между веб-сокетом и клиентом.

        Агрегирует две независимые асинхронные задачи перекачки данных с помощью
        `asyncio.gather`, блокируя выполнение до полного закрытия сессии с любой
        из сторон.

        Args:
        ----
            web_reader: Чтение из веб-сокета (запросы пользователя).
            web_writer: Запись в веб-сокет (ответы пользователю).
            data_reader: Чтение из туннельного сокета (ответы от локального хоста).
            data_writer: Запись в туннельный сокет (запросы к локальному хосту).

        """
        await asyncio.gather(
            pipe(web_reader, data_writer), pipe(data_reader, web_writer)
        )

    async def _authenticate_user(self, api_key: str) -> bool:
        return True
