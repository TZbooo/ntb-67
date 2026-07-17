# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Management of the registry of active network tunnels.

This module provides abstractions for safely tracking sessions, binding
control-plane connections, and storing asynchronous data-plane queues for the
NTB-67 project.
"""

import asyncio
from dataclasses import dataclass


@dataclass(frozen=True)
class TunnelInfoDTO:
    """
    Immutable data-transfer object with tunnel metadata.

    It is safe to pass to external layers of the application (for example, the
    REST API) without exposing internal references to sockets or queues.
    """

    subdomain: str
    client_ip: str | None
    queue_size: int


@dataclass
class TunnelSession:
    """Represents an active client tunnel session."""

    data_queue: asyncio.Queue[tuple[asyncio.StreamReader, asyncio.StreamWriter]]
    control: asyncio.StreamWriter | None = None


class TunnelRegistry:
    """Encapsulates the storage for active tunnels."""

    def __init__(self):
        """Initialize an empty tunnel registry."""
        self._tunnels: dict[str, TunnelSession] = {}

    def get(self, subdomain: str) -> TunnelSession:
        """
        Return the active tunnel session for the given subdomain.

        Args:
        ----
            subdomain: Unique name of the registered subdomain.

        Returns:
        -------
            A TunnelSession object containing the data queue and the control socket.

        Raises:
        ------
            KeyError: If no tunnel exists for the requested subdomain.

        """
        return self._tunnels[subdomain]

    def get_all_info(self) -> list[TunnelInfoDTO]:
        """
        Return a safe snapshot of metadata for all active tunnel sessions.

        The method reads the current size of the asynchronous data queue and the
        IP address of the control-plane connection, while avoiding references to
        live StreamWriter/Reader objects.

        Returns
        -------
            A list of immutable TunnelInfoDTO objects safe for external use.

        """
        snapshots: list[TunnelInfoDTO] = []
        for subdomain, session in self._tunnels.items():
            client_ip = None

            # Extract the client's IP address from the control-plane StreamWriter
            if session.control and not session.control.is_closing():
                try:
                    peername = session.control.get_extra_info("peername")
                    if peername:
                        # For IPv4/IPv6, peername is a tuple whose first element is the IP
                        client_ip = str(peername[0])
                except (RuntimeError, ValueError):
                    # In case the socket closed during iteration
                    client_ip = None

            # Read the current queue size without mutating the data
            queue_size = session.data_queue.qsize()

            snapshots.append(
                TunnelInfoDTO(
                    subdomain=subdomain,
                    client_ip=client_ip,
                    queue_size=queue_size,
                )
            )
        return snapshots

    def register(self, subdomain: str) -> TunnelSession:
        """
        Create and register a new tunnel session.

        Args:
        ----
            subdomain: Unique name of the allocated subdomain.

        Returns:
        -------
            An initialized and stored TunnelSession object.

        """
        session = TunnelSession(data_queue=asyncio.Queue())
        self._tunnels[subdomain] = session
        return session

    def activate_control(
        self, subdomain: str, writer: asyncio.StreamWriter
    ) -> None:
        """
        Attach the active control socket to the tunnel session.

        This is used during initial registration or after a client reconnects
        following a brief network interruption.

        Args:
        ----
            subdomain: The subdomain whose connection is being updated.
            writer: The control-channel StreamWriter.

        """
        self._tunnels[subdomain].control = writer

    def remove(self, subdomain: str) -> None:
        """
        Remove a tunnel session from the registry and free its subdomain.

        Args:
        ----
            subdomain: The subdomain that should be closed.

        """
        self._tunnels.pop(subdomain, None)

    def contains(self, subdomain: str) -> bool:
        """
        Check whether the given subdomain is registered in the system.

        Args:
        ----
            subdomain: Subdomain to validate.

        Returns:
        -------
            True if the session is active, otherwise False.

        """
        return subdomain in self._tunnels
