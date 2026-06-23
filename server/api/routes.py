# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Маршруты REST API управления сессиями активных туннелей."""

from typing import Any

from fastapi import APIRouter, Depends

from server.api.dependencies import APIContext, verify_admin_token

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)


@router.get("/tunnels")
async def list_active_tunnels() -> dict[str, Any]:
    """
    Возвращает структуру данных со списком всех активных туннелей в RAM.

    Returns
    -------
        Словарь со статусом выполнения и списком активных поддоменов.

    """
    server = APIContext.get_server()
    tunnels_info = server.active_tunnels.get_all_info()

    return {"status": "success", "tunnels": tunnels_info}
