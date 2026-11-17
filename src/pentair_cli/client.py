"""IntelliCenter client wrapper."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from loguru import logger
from pyintellicenter import ICConnectionHandler, ICModelController, PoolModel


class IntelliCenterClient:
    """Async client for Pentair IntelliCenter."""

    def __init__(self, host: str = "127.0.0.1", port: int = 6681, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.model = PoolModel()
        self.controller: ICModelController | None = None
        self.handler: ICConnectionHandler | None = None
        self._connected = False

    async def connect(self) -> None:
        logger.info(f"Connecting to IntelliCenter {self.host}:{self.port}")
        self.controller = ICModelController(self.host, self.model, port=self.port)
        self.handler = ICConnectionHandler(self.controller)
        try:
            async with asyncio.timeout(self.timeout):
                await self.handler.start()
        except TimeoutError as e:
            await self._abort()
            raise ConnectionError(
                f"Timed out after {self.timeout:g}s connecting to {self.host}:{self.port}"
            ) from e
        except Exception as e:
            await self._abort()
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}: {e}") from e
        self._connected = bool(self.handler.connected)
        if not self._connected:
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}")
        # Allow model to populate
        await asyncio.sleep(1)
        logger.info("Connected to IntelliCenter")

    async def _abort(self) -> None:
        if self.handler:
            try:
                await self.handler.astop()
            except Exception:  # pragma: no cover - best effort cleanup
                pass
        self._connected = False

    async def disconnect(self) -> None:
        if self.handler:
            await self.handler.astop()
            self._connected = False
            logger.info("Disconnected from IntelliCenter")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[ICModelController]:
        await self.connect()
        try:
            yield self.controller  # type: ignore[misc]
        finally:
            await self.disconnect()
