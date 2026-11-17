"""Pool control tools."""

from __future__ import annotations

from typing import Any

from pentair_cli.client import IntelliCenterClient
from pentair_cli.models.schemas import PoolStatus, SetpointResult
from pentair_cli.tools.body import apply_body_setpoint, body_fields, find_body

POOL = "POOL"


def read_pool_status(controller: Any) -> PoolStatus:
    pool = find_body(controller, POOL)
    # Pump speed: first pump in the model, fallback None
    pump_speed = None
    try:
        pumps = controller.get_pumps()
        if pumps:
            pump_speed = controller.get_pump_rpm(pumps[0].objnam)
    except Exception:
        pump_speed = None
    return PoolStatus(
        **body_fields(controller, pool),
        pump_speed=int(pump_speed) if pump_speed is not None else None,
    )


async def get_pool_status(client: IntelliCenterClient) -> PoolStatus:
    """Get current pool status."""
    async with client.session() as controller:
        return read_pool_status(controller)


async def set_pool_setpoint(
    client: IntelliCenterClient, temperature: float, unit: str | None = None
) -> SetpointResult:
    """Set pool temperature setpoint."""
    async with client.session() as controller:
        return await apply_body_setpoint(controller, POOL, temperature, unit)
