"""Tests for IntelliCenter client wrapper."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pentair_cli.client import IntelliCenterClient


def test_init_defaults():
    c = IntelliCenterClient()
    assert (c.host, c.port, c.timeout, c.is_connected) == ("127.0.0.1", 6681, 10.0, False)


async def test_connect_success():
    with (
        patch("pentair_cli.client.ICModelController"),
        patch("pentair_cli.client.ICConnectionHandler") as handler_cls,
        patch("pentair_cli.client.asyncio.sleep", new_callable=AsyncMock),
    ):
        handler = MagicMock(connected=True, start=AsyncMock())
        handler_cls.return_value = handler
        c = IntelliCenterClient()
        await c.connect()
        assert c.is_connected


async def test_connect_timeout_stops_handler():
    async def hang():
        await asyncio.sleep(10)

    with (
        patch("pentair_cli.client.ICModelController"),
        patch("pentair_cli.client.ICConnectionHandler") as handler_cls,
    ):
        handler = MagicMock(start=AsyncMock(side_effect=hang), astop=AsyncMock())
        handler_cls.return_value = handler
        c = IntelliCenterClient(timeout=0.05)
        with pytest.raises(ConnectionError, match="Timed out after 0.05s"):
            await c.connect()
        handler.astop.assert_awaited_once()


async def test_connect_error_wrapped():
    with (
        patch("pentair_cli.client.ICModelController"),
        patch("pentair_cli.client.ICConnectionHandler") as handler_cls,
    ):
        handler = MagicMock(start=AsyncMock(side_effect=OSError("refused")), astop=AsyncMock())
        handler_cls.return_value = handler
        with pytest.raises(ConnectionError, match="refused"):
            await IntelliCenterClient().connect()
