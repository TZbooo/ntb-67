# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Вспомогательные утилиты для работы с сетевыми потоками Asyncio.

Предоставляет низкоуровневые инструменты для безопасного закрытия сокетов
и организации однонаправленной асинхронной перекачки байт (пайпинга) трафика.
"""

import asyncio


async def close_writer(writer: asyncio.StreamWriter) -> None:
    """
    Безопасно завершает работу сокета и закрывает StreamWriter.

    Подавляет любые возникающие исключения (например, ConnectionResetError),
    гарантируя корректное освобождение системных ресурсов.

    Args:
    ----
        writer: Экземпляр закрываемого асинхронного потока записи.

    """
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:
        pass


async def pipe(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    """
    Организует односторонний стриминг байт из reader в writer.

    Читает данные из входящего потока блоками по 4096 байт и перенаправляет их
    в поток записи до тех пор, пока не будет достигнут EOF или не произойдет
    сетевой сбой. В конце автоматически закрывает целевой writer.

    Args:
    ----
        reader: Асинхронный поток для чтения данных.
        writer: Асинхронный поток для записи данных.

    """
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
        await close_writer(writer)
