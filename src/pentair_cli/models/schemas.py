"""Result schemas: the CLI's public output contract (text and --json).

Field names use the CLI's own vocabulary (see ``vocabulary.py``), not
IntelliCenter attribute names: ``id`` (not objnam), ``name`` (not sname),
``kind``/``type`` (not objtype/subtype), ``on`` (not STATUS).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SystemInfo(BaseModel):
    name: str | None = Field(default=None, description="Installation name")
    firmware: str | None = Field(default=None, description="Controller firmware version")
    unit: str | None = Field(default=None, description="Temperature unit: F or C")
    id: str | None = Field(default=None, description="System object ID")
    unique_id: str | None = None


class ModelSummary(BaseModel):
    total: int
    by_kind: dict[str, int] = Field(description="Object counts keyed by plural kind")


class Ref(BaseModel):
    """Anything on the controller: circuit, body, heater, pump..."""

    id: str = Field(description="Controller ID, e.g. C0003. Always unique.")
    name: str | None = Field(default=None, description="Display name. May not be unique.")
    kind: str | None = Field(default=None, description="circuit, body, heater, pump, ...")
    type: str | None = Field(default=None, description="e.g. Generic, Spa, IntelliBrite light")
    on: bool | None = Field(default=None, description="On/off state; null if not applicable")


class Light(Ref):
    effect: str | None = Field(default=None, description="Current color effect name")


class ObjectDetail(Ref):
    attributes: dict[str, Any] = Field(
        default_factory=dict, description="Raw IntelliCenter attributes (unstable, for debugging)"
    )


class BodyStatus(BaseModel):
    id: str | None = Field(default=None, description="Body ID, e.g. B1101")
    name: str | None = None
    temperature: float | None = Field(default=None, description="Current water temperature")
    setpoint: float | None = Field(default=None, description="Heating setpoint")
    heat_mode: str | None = Field(
        default=None, description="Configured heat mode, e.g. Off, Heater, Solar Preferred"
    )
    heat_source: str | None = Field(default=None, description="Selected heater name")
    heat_source_id: str | None = Field(default=None, description="Selected heater ID")
    heating: bool | None = Field(
        default=None, description="True only while the water is actively being heated"
    )
    unit: str | None = Field(default=None, description="Temperature unit: F or C")


class PoolStatus(BodyStatus):
    pump_rpm: int | None = Field(default=None, description="First pump speed, RPM")


class SpaStatus(BodyStatus):
    pass


class SetpointResult(BaseModel):
    ok: bool = True
    id: str
    name: str | None = None
    setpoint: int = Field(description="Setpoint sent to the controller, in `unit`")
    unit: str
    requested: float
    requested_unit: str
    confirmed: bool = Field(default=False, description="Controller reported the new setpoint")
    reported_setpoint: float | None = Field(
        default=None, description="Setpoint the controller last reported"
    )


class CircuitStateResult(BaseModel):
    ok: bool = True
    id: str
    name: str | None = None
    on: bool


class LightEffect(BaseModel):
    name: str
    code: str


class LightEffectResult(BaseModel):
    ok: bool = True
    id: str
    name: str | None = None
    effect: str
    effect_code: str


class Overview(BaseModel):
    system: SystemInfo | None = None
    pool: PoolStatus | None = None
    spa: SpaStatus | None = None
    circuits_on: list[Ref] = Field(default_factory=list)
