# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
# 
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription. 
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

import time
import hmac
import hashlib
import secrets
from .config import SECRET_KEY, TUNNEL_LIVE_TIME_SECONDS


def generate_free_subdomain() -> str:
    """Генерирует случайный поддомен с временной меткой и криптографической подписью.
    
    Формат: {rand_bytes}-{hex_timestamp}-{signature}
    """

    rand_bytes = secrets.token_hex(4)
    
    # Берем текущее время (округляем до секунд) и переводим в hex
    timestamp_hex = hex(int(time.time()))[2:]  # например: '665af380'
        
    payload = f"{rand_bytes}:{timestamp_hex}"
        
    # Подписываем весь payload целиком
    signature = hmac.new(
        SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:8]
    
    return f"{rand_bytes}-{timestamp_hex}-{signature}"


def is_valid_subdomain(subdomain: str) -> bool:
    """Проверяет валидность поддомена и то, что он был создан менее 1 часа назад."""
        
    # Проверяем структуру (теперь должно быть ровно два дефиса)
    if subdomain.count("-") != 2:
        return False

    rand_bytes, timestamp_hex, signature = subdomain.split("-", 2)
    
    # 1. Сначала проверяем криптографическую подпись
    payload = f"{rand_bytes}:{timestamp_hex}"
    expected_signature = hmac.new(
        SECRET_KEY.encode(), payload.encode(), hashlib.sha256
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