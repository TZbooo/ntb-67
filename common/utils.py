import asyncio


async def close_writer(writer: asyncio.StreamWriter) -> None:
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:
        pass


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Односторонняя перекачка байт reader → writer до EOF или ошибки."""
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