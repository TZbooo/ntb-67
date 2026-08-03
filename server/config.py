# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Environment and database configuration for the NTB-67 project.

This module loads environment variables and exposes them as a typed Pydantic
settings object.
"""

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProjectSettings(BaseSettings):
    """Project configuration for NTB-67 loaded from environment variables."""

    DOMAIN: str

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DB_HOST: str
    DB_PORT: int

    model_config = SettingsConfigDict(extra="ignore")

    @computed_field
    @property
    def database_url(self) -> str:
        """Build the PostgreSQL connection string from the configured settings."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.POSTGRES_DB}"
        )


project_settings = ProjectSettings()  # type: ignore[call-arg]
