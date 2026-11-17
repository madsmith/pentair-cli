"""Spa control tools."""

from __future__ import annotations

from typing import Any

from pentair_cli.client import IntelliCenterClient
from pentair_cli.models.schemas import SetpointResult, SpaStatus
from pentair_cli.tools.body import apply_body_setpoint, body_fields, find_body

SPA = "SPA"


def read_spa_status(controller: Any) -> SpaStatus:
    return SpaStatus(**body_fields(controller, find_body(controller, SPA)))


async def get_spa_status(client: IntelliCenterClient) -> SpaStatus:
    """Get current spa status."""
    async with client.session() as controller:
        return read_spa_status(controller)


async def set_spa_setpoint(
    client: IntelliCenterClient, temperature: float, unit: str | None = None
) -> SetpointResult:
    """Set spa temperature setpoint."""
    async with client.session() as controller:
        return await apply_body_setpoint(controller, SPA, temperature, unit)
