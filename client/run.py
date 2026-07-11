# -*- coding: utf-8 -*-
# ntb-67 — Asyncio Tunneling Proxy Server
# Copyright (c) 2026 Timur Zolotov (netbiom). All rights reserved.
#
# This source code is licensed under the NTB-67 Source-Available Commercial License.
# Commercial use requires a valid paid subscription.
# See the LICENSE file in the root directory for full terms and conditions.
# For commercial inquiries, contact Telegram: https://t.me/netbiom

"""
CLI entrypoint for the NTB-67 tunnel client.

This module provides the command-line interface for authenticating the client,
starting a local port tunnel, and launching the local control UI. It connects
configuration, the FastAPI daemon, and terminal-based management into a single
developer-friendly workflow for exposing local services through NTB-67.
"""

import asyncio
import configparser
import os
import platform
import subprocess

import typer
import uvicorn
from platformdirs import user_config_dir

from .daemon import app as fastapi_app
from .tui import TerminalUserInterface

app = typer.Typer(
    help="ntb-67 — High-performance asynchronous tunnel for local ports."
)
config_app = typer.Typer(help="Manage client configuration.")
app.add_typer(config_app, name="config")

CONFIG_DIR = user_config_dir("ntb-67")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.ini")


def get_saved_api_key() -> str | None:
    """Load a saved API key from the config file or environment variable."""
    if key := os.environ.get("NTB_API_KEY"):
        return key
    if os.path.exists(CONFIG_FILE):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        return config.get("AUTH", "api_key", fallback=None)
    return None


@app.command()
def auth(
    api_key: str = typer.Argument(
        ..., help="API key for the client from the Telegram bot"
    ),
):
    """Save the API key for server authentication."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config = configparser.ConfigParser()
    config["AUTH"] = {"api_key": api_key}

    with open(CONFIG_FILE, "w") as f:
        config.write(f)

    if platform.system() != "Windows":
        os.chmod(CONFIG_FILE, 0o600)

    typer.secho("✅ API key saved successfully!", fg=typer.colors.GREEN)


@config_app.command(name="edit")
def config_edit():
    """Open the configuration file in a text editor."""
    if not os.path.exists(CONFIG_FILE):
        typer.secho("❌ Configuration file not found.", fg=typer.colors.RED)
        return

    typer.echo(f"📂 Opening configuration: {CONFIG_FILE}")

    if platform.system() == "Windows":
        subprocess.run(f'start "" "{CONFIG_FILE}"', shell=True)
    else:
        typer.launch(CONFIG_FILE)


@app.command()
def start(
    local_port: int = typer.Argument(
        ..., help="Local port to expose (for example, 8000)"
    ),
    host: str = typer.Option("24tunl.ru", help="Host of the remote NTB server"),
    port: int = typer.Option(
        9000, help="Control port of the remote NTB server"
    ),
    api_port: int = typer.Option(8080, help="Port where FastAPI will run"),
):
    """Start tunneling for a local port."""
    api_key = get_saved_api_key()
    if not api_key:
        typer.secho(
            "❌ Error: API key not found!", fg=typer.colors.RED, err=True
        )
        typer.echo("Please run: ntb-67 auth <your_key>")
        raise typer.Exit(code=1)

    fastapi_app.state.tunnel_config = {
        "host": host,
        "port": port,
        "local_port": local_port,
        "api_key": api_key,
    }

    config = uvicorn.Config(
        app=fastapi_app,
        host="127.0.0.1",
        port=api_port,
        log_config=None,
    )
    server = uvicorn.Server(config)

    api_base_url = f"http://127.0.0.1:{api_port}"
    tui_app = TerminalUserInterface(api_url=api_base_url)

    async def run_orchestrator() -> None:
        fastapi_task = asyncio.create_task(server.serve())

        try:
            await tui_app.run_async()
        finally:
            server.should_exit = True
            await fastapi_task

    try:
        asyncio.run(run_orchestrator())
    except KeyboardInterrupt:
        pass
    finally:
        typer.echo("\n👋 All systems stopped. See you next time!")
        raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
