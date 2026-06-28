# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
Конфигурация окружения и параметров базы данных проекта ntb-67.

Загружает переменные среды из файлов окружения и предоставляет их в виде
типизированного объекта настроек Pydantic.
"""

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProjectSettings(BaseSettings):
    """Конфигурация проекта ntb-67, загружаемая из переменных окружения."""

    SECRET_KEY: str
    TUNNEL_LIVE_TIME_HOURS: float

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DB_HOST: str
    DB_PORT: int

    model_config = SettingsConfigDict(extra="ignore")

    @computed_field
    @property
    def tunnel_live_time_seconds(self) -> float:
        """Возвращает время жизни туннеля, переведенное из часов в секунды."""
        return self.TUNNEL_LIVE_TIME_HOURS * 3600

    @computed_field
    @property
    def database_url(self) -> str:
        """Формирует строку подключения к PostgreSQL на основе параметров."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.POSTGRES_DB}"
        )


project_settings = ProjectSettings()  # type: ignore[call-arg]
