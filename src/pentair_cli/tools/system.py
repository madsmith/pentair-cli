"""System-level tools."""

from __future__ import annotations

from typing import Any

from pentair_cli.client import IntelliCenterClient
from pentair_cli.models.schemas import ModelSummary, ObjectRef, Overview, SystemInfo
from pentair_cli.tools import NotFoundError
from pentair_cli.tools.common import object_ref


def read_system_info(controller: Any) -> SystemInfo:
    sys_info = controller.system_info
    if not sys_info:
        raise RuntimeError("System info not available")
    return SystemInfo(
        prop_name=getattr(sys_info, "prop_name", None),
        sw_version=getattr(sys_info, "sw_version", None),
        uses_metric=getattr(sys_info, "uses_metric", None),
        objnam=getattr(sys_info, "objnam", None),
        unique_id=getattr(sys_info, "unique_id", None),
    )


def read_model_summary(controller: Any) -> ModelSummary:
    counts: dict[str, int] = {}
    for obj in controller.model.objects.values():
        t = getattr(obj, "objtype", None) or type(obj).__name__
        counts[t] = counts.get(t, 0) + 1
    return ModelSummary(
        num_objects=controller.model.num_objects, object_types=dict(sorted(counts.items()))
    )


def read_overview(controller: Any) -> Overview:
    """Everything an operator usually wants, from a single connection."""
    from pentair_cli.tools.pool import read_pool_status
    from pentair_cli.tools.spa import read_spa_status

    def attempt(fn):
        try:
            return fn(controller)
        except (NotFoundError, RuntimeError):
            return None

    circuits_on: list[ObjectRef] = [
        object_ref(c)
        for c in controller.get_circuits()
        if getattr(c, "status", None) == getattr(c, "on_status", "ON")
    ]
    return Overview(
        system=attempt(read_system_info),
        pool=attempt(read_pool_status),
        spa=attempt(read_spa_status),
        circuits_on=circuits_on,
    )


async def get_system_info(client: IntelliCenterClient) -> SystemInfo:
    """Get IntelliCenter system information."""
    async with client.session() as controller:
        return read_system_info(controller)


async def get_model_summary(client: IntelliCenterClient) -> ModelSummary:
    """Return a summary of the IntelliCenter model objects."""
    async with client.session() as controller:
        return read_model_summary(controller)


async def get_overview(client: IntelliCenterClient) -> Overview:
    async with client.session() as controller:
        return read_overview(controller)
