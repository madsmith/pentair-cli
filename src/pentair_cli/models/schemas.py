"""Pydantic schemas for command results (rendered as text or JSON)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SystemInfo(BaseModel):
    prop_name: str | None = None
    sw_version: str | None = None
    uses_metric: bool | None = None
    objnam: str | None = None
    unique_id: str | None = None


class ModelSummary(BaseModel):
    num_objects: int
    object_types: dict[str, int]


class BodyStatus(BaseModel):
    body: str | None = Field(default=None, description="Body objnam")
    name: str | None = Field(default=None, description="Body display name (sname)")
    temperature: float | None = Field(default=None, description="Current water temperature")
    setpoint: float | None = Field(default=None, description="Heating setpoint temperature")
    heater_on: bool | None = None
    unit: str | None = Field(default=None, description="Temperature unit: F or C")


class PoolStatus(BodyStatus):
    pump_speed: int | None = Field(default=None, description="First pump RPM")


class SpaStatus(BodyStatus):
    pass


class SetpointResult(BaseModel):
    ok: bool = True
    body: str
    temperature: int = Field(description="Setpoint sent to the controller (system unit)")
    unit: str
    requested: float
    requested_unit: str
    verified_setpoint: float | None = None
    verified: bool = False


class ObjectRef(BaseModel):
    objnam: str
    sname: str | None = None
    type: str | None = None
    subtype: str | None = None
    status: str | None = None


class ObjectDetail(ObjectRef):
    properties: dict[str, Any] = Field(default_factory=dict)


class CircuitStateResult(BaseModel):
    ok: bool = True
    objnam: str
    resolved_objnam: str
    state: bool


class LightEffectResult(BaseModel):
    ok: bool = True
    objnam: str
    resolved_objnam: str
    effect: str
    effect_name: str | None = None


class LightEffect(BaseModel):
    code: str
    name: str


class Overview(BaseModel):
    system: SystemInfo | None = None
    pool: PoolStatus | None = None
    spa: SpaStatus | None = None
    circuits_on: list[ObjectRef] = Field(default_factory=list)
