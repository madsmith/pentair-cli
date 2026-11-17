"""Shared body-of-water (pool/spa) logic."""

from __future__ import annotations

import asyncio
from typing import Any

from pyintellicenter import HeaterType

from pentair_cli.models.schemas import SetpointResult
from pentair_cli.tools.common import resolve

# Sanity bounds for setpoints, in Fahrenheit (≈4.5–40 °C).
MIN_SETPOINT_F = 40.0
MAX_SETPOINT_F = 104.0


def system_unit(controller: Any) -> str:
    info = controller.system_info
    return "C" if info is not None and getattr(info, "uses_metric", False) else "F"


def find_body(controller: Any, name: str) -> Any:
    return resolve(controller.get_bodies(), name, "body")


def heat_mode_name(mode: HeaterType | None) -> str | None:
    """HeaterType.SOLAR_PREFERRED -> "Solar Preferred"."""
    if mode is None:
        return None
    return mode.name.replace("_", " ").title().replace("Ultra Temp", "UltraTemp")


def body_fields(controller: Any, body: Any) -> dict[str, Any]:
    mode = controller.get_body_heat_mode(body.objnam)
    heater = None if mode == HeaterType.OFF else controller.get_heater_for_body(body.objnam)
    return {
        "id": body.objnam,
        "name": getattr(body, "sname", None),
        "temperature": controller.get_body_temperature(body.objnam),
        "setpoint": controller.get_body_heating_setpoint(body.objnam),
        "heat_mode": heat_mode_name(mode),
        "heat_source": getattr(heater, "sname", None) if heater else None,
        "heat_source_id": heater.objnam if heater else None,
        "heating": bool(controller.is_body_heating(body.objnam)),
        "unit": system_unit(controller),
    }


def convert(temperature: float, from_unit: str, to_unit: str) -> float:
    if from_unit == to_unit:
        return temperature
    if from_unit == "F":
        return (temperature - 32) * 5.0 / 9.0
    return temperature * 9.0 / 5.0 + 32


async def apply_body_setpoint(
    controller: Any,
    name: str,
    temperature: float,
    unit: str | None = None,
    verify_seconds: int = 5,
) -> SetpointResult:
    """Set a body's heating setpoint.

    ``unit`` is the unit of ``temperature`` ("F" or "C"); when omitted the
    controller's own unit is assumed (the same unit ``status`` reports).
    """
    body = find_body(controller, name)
    sys_unit = system_unit(controller)
    requested_unit = (unit or sys_unit).upper()
    in_f = convert(temperature, requested_unit, "F")
    if not MIN_SETPOINT_F <= in_f <= MAX_SETPOINT_F:
        lo, hi = (
            convert(MIN_SETPOINT_F, "F", requested_unit),
            convert(MAX_SETPOINT_F, "F", requested_unit),
        )
        raise ValueError(
            f"Setpoint {temperature:g}°{requested_unit} outside safe range "
            f"{lo:.0f}–{hi:.0f}°{requested_unit}"
        )
    # IntelliCenter expects an integer setpoint in its own unit.
    temperature_int = int(round(convert(temperature, requested_unit, sys_unit)))
    await controller.set_heat_mode(body.objnam, HeaterType.HEATER)
    await asyncio.sleep(0.2)
    await controller.set_heating_setpoint(body.objnam, temperature_int)
    # Allow controller time to update model, retry a few times
    new_setpoint = None
    for _ in range(verify_seconds):
        await asyncio.sleep(1.0)
        new_setpoint = controller.get_body_heating_setpoint(body.objnam)
        if new_setpoint == temperature_int:
            break
    return SetpointResult(
        id=body.objnam,
        name=getattr(body, "sname", None),
        setpoint=temperature_int,
        unit=sys_unit,
        requested=temperature,
        requested_unit=requested_unit,
        confirmed=new_setpoint == temperature_int,
        reported_setpoint=new_setpoint,
    )
