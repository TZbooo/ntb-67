# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Клиентское приложение для динамического подключения к серверу маршрутизации.

Данный модуль отвечает за авторизацию поддомена на сервере, обработку сигналов
выделения дата-каналов и проброс входящих пакетов на локальный порт разработчика.
"""

import asyncio
import configparser
import os

import typer
from platformdirs import user_config_dir

from common.utils import close_writer, pipe

app = typer.Typer(
    help="ntb-67 — Скоростной асинхронный туннель для локальных портов."
)
CONFIG_DIR = user_config_dir("ntb-67")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.ini")


class NTBClient:
    """Клиент туннелирования с поддержкой динамических поддоменов."""

    def __init__(
        self, server_host: str, server_port: int, local_port: int, api_key: str
    ) -> None:
        """
        Инициализирует экземпляр NTBClient.

        Args:
        ----
            server_host: IP-адрес или домен удаленного сервера маршрутизации.
            server_port: Управляющий TCP-порт удаленного сервера.
            local_port: Сетевой порт локального веб-сервера для проброса.
            api_key: API ключ клиента

        """
        self.server_host = server_host
        self.server_port = server_port
        self.local_port = local_port
        self.api_key = api_key
        self.subdomain = None

    async def open_connection(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """
        Устанавливает низкоуровневое TCP-соединение с сервером ntb-67.

        Returns
        -------
            Кортеж из асинхронных объектов чтения (StreamReader) и записи
            (StreamWriter) для работы с сокетом.

        """
        return await asyncio.open_connection(self.server_host, self.server_port)

    async def start(self) -> None:
        """
        Запускает бесконечный цикл удержание сессии и обработки туннеля.

        При возникновении сетевых сбоев или обрыве сокета функция переходит в
        режим ожидания и инициирует повторное подключение, стараясь сохранить
        ранее выделенный поддомен.
        """
        while True:
            try:
                await self._start_tunnel()
            except Exception as e:
                print(f"❌ Ошибка соединения с сервером: {e}")
                print("⏳ Переподключение через 5 секунд...")
                await asyncio.sleep(5)

    async def _start_tunnel(self) -> None:
        """
        Инициализирует Control Plane и обрабатывает входящие команды сервера.

        Регистрирует сессию на удаленном брокере, запускает фоновую задачу
        heartbeat-валидации и ожидает управляющие триггеры на открытие
        новых мостов передачи данных.

        Raises
        ------
            Exception: При критических сетевых ошибках в процессе удержания
                активного управляющего канала.

        """
        reader, writer = await self.open_connection()

        if self.subdomain:
            # Отправляем запрос на инициализацию с указанием поддомена
            writer.write(
                f"INIT:{self.api_key}:{self.subdomain}\n".encode("utf-8")
            )
            await writer.drain()
        else:
            # Отправляем запрос на инициализацию без указания поддомена
            writer.write(f"INIT:{self.api_key}\n".encode("utf-8"))
            await writer.drain()

        # Ждем ответ от сервера с назначенным UUID/хэшем
        response_bytes = await reader.readline()
        if not response_bytes:
            await close_writer(writer)
            return

        response = response_bytes.decode("utf-8").strip()
        if response.startswith("ASSIGNED:"):
            self.subdomain = response.split(":", 1)[1].strip()

            print("\n" + "=" * 50)
            print("🎉 Туннель успешно запущен!")
            print(f"🔗 Публичный адрес:  https://{self.subdomain}.24tunl.ru")
            print(f"🏠 Локальный порт:   http://127.0.0.1:{self.local_port}")
            print("=" * 50 + "\n")
        elif response.startswith("ERROR:"):
            error_msg = response.split(":", 1)[1].strip()
            print(f"❌ Сервер вернул ошибку: {error_msg}")
            await close_writer(writer)
            await asyncio.sleep(5)
            return
        else:
            print("❌ Сервер отказал в инициализации туннеля.")
            await close_writer(writer)
            await asyncio.sleep(5)
            return

        heartbeat_task = asyncio.create_task(self.start_heartbeat(writer))

        try:
            while True:
                line_bytes = await reader.readline()
                if not line_bytes:
                    break

                cmd = line_bytes.decode("utf-8").strip()
                if cmd == "REQUEST_CONN":
                    asyncio.create_task(self.spawn_data_connection())
        finally:
            heartbeat_task.cancel()
            await close_writer(writer)

    async def spawn_data_connection(self) -> None:
        """
        Создает изолированный Data Plane канал для обработки HTTP-запроса.

        Инициирует выделенное параллельное сокет-соединение с сервером ntb-67,
        маркирует его уникальным идентификатором поддомена и связывает его
        симметричным мостом с целевым локальным портом разработчика.
        """
        try:
            # Открываем сокет к серверу туннелирования
            server_reader, server_writer = await self.open_connection()

            # Маркируем сокет, чтобы сервер понял, какому поддомену он принадлежит
            server_writer.write(f"DATA:{self.subdomain}\n".encode("utf-8"))
            await server_writer.drain()

            # Открываем сокет к нашему локальному сайту/серверу (например, к порту 3000 или 80)
            local_reader, local_writer = await asyncio.open_connection(
                "127.0.0.1", self.local_port
            )

        except Exception as e:
            print(f"❌ Не удалось связать дата-каналы: {e}")
            return

        # Начинаем качать байты в обе стороны
        await asyncio.gather(
            pipe(server_reader, local_writer), pipe(local_reader, server_writer)
        )

    async def start_heartbeat(self, writer: asyncio.StreamWriter) -> None:
        """
        Обеспечивает постоянную отправку отладочных пакетов (Keep-Alive).

        Каждые 10 секунд отправляет маркер PING в управляющий сокет,
        предотвращая его принудительное закрытие межсетевыми экранами (NAT/Firewall)
        по таймауту неактивности.

        Args:
        ----
            writer: Экземпляр асинхронного потока записи управляющего сокета.

        """
        try:
            while True:
                await asyncio.sleep(10)
                writer.write(b"PING\n")
                await writer.drain()
        except Exception:
            pass


def get_saved_api_key() -> str | None:
    """Получает сохраненный API ключ из конфигурационного файла или переменной окружения."""
    if key := os.environ.get("NTB_API_KEY"):
        return key
    if os.path.exists(CONFIG_FILE):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        return config.get("AUTH", "api_key", fallback=None)
    return None


@app.command()
def auth(
    api_key: str = typer.Argument(
        ..., help="Ключ API клиента из Telegram-бота"
    ),
):
    """Сохранить API ключ для авторизации на сервере."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config = configparser.ConfigParser()
    config["AUTH"] = {"api_key": api_key}

    with open(CONFIG_FILE, "w") as f:
        config.write(f)
    os.chmod(CONFIG_FILE, 0o600)

    typer.secho("✅ API ключ успешно сохранен!", fg=typer.colors.GREEN)


@app.command()
def start(
    local_port: int = typer.Argument(
        ..., help="Локальный порт для проброса (например, 8000)"
    ),
    host: str = typer.Option("24tunl.ru", help="Хост удаленного сервера NTB"),
    port: int = typer.Option(
        9000, help="Управляющий порт удаленного сервера NTB"
    ),
):
    """Запустить туннелирование для локального порта."""
    api_key = get_saved_api_key()
    if not api_key:
        typer.secho(
            "❌ Ошибка: API ключ не найден!", fg=typer.colors.RED, err=True
        )
        typer.echo(
            "Пожалуйста, сначала выполните команду: ntb-67 auth <ваш_ключ>"
        )
        raise typer.Exit(code=1)

    try:
        client = NTBClient(
            server_host=host,
            server_port=port,
            local_port=local_port,
            api_key=api_key,
        )
        asyncio.run(client.start())
    except KeyboardInterrupt:
        typer.echo("\n👋 Туннель закрыт пользователем. До встречи!")
        raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
