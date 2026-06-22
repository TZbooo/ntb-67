# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
# 
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription. 
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom


def extract_subdomain(header_chunk: bytes, base_domain: str = ".24tunl.ru") -> str | None:
    """Вытаскивает поддомен из сырого HTTP-заголовка Host."""

    try:
        headers_text = header_chunk.decode('utf-8', errors='ignore')
        for line in headers_text.split('\r\n'):
            if line.lower().startswith('host:'):
                # Пример: "Host: app.24tunl.ru" -> "app.24tunl.ru"
                host_value = line.split(':', 1)[1].strip()
                # Вытаскиваем поддомен (все что до первой точки)
                if base_domain in host_value:
                    return host_value.split(base_domain)[0].lower()
                # На случай локальных тестов через localhost:8000
                return host_value.split('.')[0].lower()
    except Exception:
        pass
    return None