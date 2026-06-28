# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Криптографическая генерация и валидация временных поддоменов.

Предоставляет утилиты для создания подписанных с помощью HMAC-SHA256 поддоменов
и проверки их валидности, защищая инфраструктуру ntb-67 от подделки адресов
и несанкционированного долгосрочного использования бесплатных сессий.
"""

import hashlib
import hmac
import secrets
import time

from .config import project_settings


def generate_free_subdomain() -> str:
    """
    Генерирует случайный поддомен с временной меткой и HMAC-подписью.

    Строит строку в формате: {rand_bytes}-{hex_timestamp}-{signature},
    где подпись вычисляется от полезной нагрузки на основе секретного ключа.

    Returns
    -------
        Сгенерированная строка уникального временного поддомена.

    """
    rand_bytes = secrets.token_hex(4)

    # Берем текущее время (округляем до секунд) и переводим в hex
    timestamp_hex = hex(int(time.time()))[2:]  # например: '665af380'

    payload = f"{rand_bytes}:{timestamp_hex}"

    # Подписываем весь payload целиком
    signature = hmac.new(
        project_settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:8]

    return f"{rand_bytes}-{timestamp_hex}-{signature}"


def is_valid_subdomain(subdomain: str) -> bool:
    """
    Проверяет целостность поддомена и ограничение по времени его жизни.

    Выполняет парсинг структуры, сверку криптографической подписи HMAC
    в режиме защиты от timing-атак и проверяет соответствие TTL.

    Args:
    ----
        subdomain: Строка проверяемого поддомена для валидации.

    Returns:
    -------
        True, если подпись подлинна и лимит времени не исчерпан, иначе False.

    """
    # Проверяем структуру (теперь должно быть ровно два дефиса)
    if subdomain.count("-") != 2:
        return False

    rand_bytes, timestamp_hex, signature = subdomain.split("-", 2)

    # 1. Сначала проверяем криптографическую подпись
    payload = f"{rand_bytes}:{timestamp_hex}"
    expected_signature = hmac.new(
        project_settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:8]

    # Защита от timing-атак: если подпись левая — сразу выходим
    if not hmac.compare_digest(signature, expected_signature):
        return False

    # 2. Подпись верна, теперь проверяем время жизни (Time-to-Live)
    try:
        # Переводим hex-таймстамп обратно в int (секунды)
        created_time = int(timestamp_hex, 16)
    except ValueError:
        return (
            False  # На случай, если в hex_timestamp передали невалидные символы
        )

    current_time = int(time.time())

    if current_time - created_time > project_settings.tunnel_live_time_seconds:
        print(
            f"⏱️ Поддомен {subdomain} просрочен (создан более {project_settings.tunnel_live_time_seconds} секунд назад)"
        )
        return False

    return True
