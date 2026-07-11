# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""REST API routes for managing active tunnel sessions."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from common.utils import close_writer
from server.api.dependencies import APIContext, verify_admin_token

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)


@router.get("/tunnels")
async def list_active_tunnels() -> dict[str, Any]:
    """
    Return a structure containing all active tunnels in memory.

    Returns
    -------
        A dictionary with the operation status and the list of active subdomains.

    """
    server = APIContext.get_server()
    tunnels_info = server.active_tunnels.get_all_info()

    return {"status": "success", "tunnels": tunnels_info}


@router.delete("/tunnel/{subdomain}")
async def delete_active_tunnel(subdomain: str) -> dict[str, Any]:
    """
    Force-close and remove an active tunnel by its subdomain.

    Args:
    ----
        subdomain: The identifier (subdomain) of the tunnel to remove.

    Returns:
    -------
        A dictionary describing the operation status and the success message.

    Raises:
    ------
        HTTPException: 404 if the tunnel is not found; 500 if the tunnel has no control socket.

    """
    server = APIContext.get_server()

    if not server.active_tunnels.contains(subdomain):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tunnel with {subdomain=} not found",
        )

    tunnel = server.active_tunnels.get(subdomain)
    if not tunnel.control:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tunnel with {subdomain=} has no control socket",
        )

    server.active_tunnels.remove(subdomain)
    await close_writer(tunnel.control)

    return {
        "status": "success",
        "message": f"Tunnel with {subdomain=} closed and removed",
    }
