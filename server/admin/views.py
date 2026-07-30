# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""Admin views for managing users and roles in the application."""

from sqladmin import ModelView

from server.models import Role, User, UserSubdomain


class UserAdmin(ModelView, model=User):
    """Admin view for managing user accounts."""

    column_list = [
        User.id,
        User.username,
        User.is_active,
        User.role,
        User.api_key,
        User.max_tunnels,
    ]
    column_searchable_list = [User.username]
    form_columns = [
        User.username,
        User.is_active,
        User.role,
        User.api_key,
        User.max_tunnels,
    ]
    icon = "fa-solid fa-user"


class RoleAdmin(ModelView, model=Role):
    """Admin view for managing user roles and permissions."""

    column_list = [Role.id, Role.name, Role.permissions]
    form_columns = [Role.name, Role.permissions]
    icon = "fa-solid fa-user-shield"


class UserSubdomainAdmin(ModelView, model=UserSubdomain):
    """Admin view for managing user subdomains."""

    column_list = [
        UserSubdomain.id,
        UserSubdomain.subdomain,
        UserSubdomain.user,
    ]
    form_columns = [UserSubdomain.subdomain, UserSubdomain.user]
    icon = "fa-solid fa-globe"
