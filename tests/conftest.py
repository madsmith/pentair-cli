"""Pytest configuration and fixtures."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest
from pyintellicenter import HeaterType

from pentair_cli.config import ENV_PREFIX, SETTING_KEYS


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Never read the developer's real env vars or ~/.config."""
    for key in SETTING_KEYS:
        monkeypatch.delenv(ENV_PREFIX + key.upper(), raising=False)
    monkeypatch.delenv("PENTAIR_CLI_CONFIG", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))


def obj(
    objnam: str,
    sname: str | None,
    objtype: str = "CIRCUIT",
    subtype: str = "GENERIC",
    status: str = "OFF",
    **props: Any,
) -> SimpleNamespace:
    return SimpleNamespace(
        objnam=objnam,
        sname=sname,
        objtype=objtype,
        subtype=subtype,
        status=status,
        on_status="ON",
        properties={"SNAME": sname, **props},
    )


class FakeController:
    """Minimal stand-in for pyintellicenter.ICModelController."""

    def __init__(self, metric: bool = False) -> None:
        self.system_info = SimpleNamespace(
            prop_name="Test", sw_version="3.008", uses_metric=metric, objnam="_5451", unique_id="u1"
        )
        self.bodies = [obj("B1101", "Pool", "BODY", "POOL"), obj("B1202", "Spa", "BODY", "SPA")]
        self.circuits = [
            obj("C0001", "Spa", subtype="SPA", status="ON"),
            obj("C0003", "Jets"),
            obj("C0015", "Cleaner"),
            obj("X0043", "Cleaner", subtype="Generic"),
            obj("_A111", "All Lights On", subtype="ALL", status="PERMIT"),
            obj("C0016", "Step Light", subtype="LIGHT"),
            obj("C0017", "Step Light", subtype="LIGHT"),
        ]
        self.lights = [obj("C0009", "Pool Lights", subtype="INTELLI")]
        self.heaters = {"H0001": obj("H0001", "Gas Heater", "HEATER", "GENERIC", "ON")}
        self.heat_modes = {"B1101": HeaterType.HEATER, "B1202": HeaterType.OFF}
        self.body_heater = {"B1101": "H0001", "B1202": "H0001"}
        self.heating = {"B1101": False, "B1202": False}
        self.temps = {"B1101": 56, "B1202": 78}
        self.setpoints = {"B1101": 55, "B1202": 72}
        self.calls: list[tuple] = []
        objects = {o.objnam: o for o in [*self.bodies, *self.circuits, *self.lights]}
        self.model = SimpleNamespace(objects=objects, num_objects=len(objects))

    def get_bodies(self):
        return self.bodies

    def get_circuits(self):
        return self.circuits

    def get_lights(self):
        return self.lights

    def get_pumps(self):
        return [obj("PMP01", "Pump", "PUMP")]

    def get_pump_rpm(self, objnam):
        return 3000

    def get_body_temperature(self, o):
        return self.temps[o]

    def get_body_heating_setpoint(self, o):
        return self.setpoints[o]

    def is_body_heating(self, o):
        return self.heating[o]

    def get_body_heat_mode(self, o):
        return self.heat_modes[o]

    def get_heater_for_body(self, o):
        return self.heaters.get(self.body_heater[o])

    def get_all_entities(self):
        return {"bodies": self.bodies, "circuits": self.circuits, "lights": self.lights}

    async def set_heat_mode(self, o, mode):
        self.calls.append(("heat_mode", o, mode))

    async def set_heating_setpoint(self, o, t):
        self.calls.append(("setpoint", o, t))
        self.setpoints[o] = t

    async def set_circuit_state(self, o, s):
        self.calls.append(("circuit", o, s))

    async def set_light_effect(self, o, e):
        self.calls.append(("effect", o, e))


class FakeClient:
    def __init__(self, controller: FakeController | None = None, error: Exception | None = None):
        self.controller = controller or FakeController()
        self.error = error

    @asynccontextmanager
    async def session(self):
        if self.error:
            raise self.error
        yield self.controller


@pytest.fixture
def controller() -> FakeController:
    return FakeController()


@pytest.fixture
def no_sleep(monkeypatch):
    async def _sleep(*_a, **_k):
        return None

    monkeypatch.setattr("pentair_cli.tools.body.asyncio.sleep", _sleep)


@pytest.fixture
def fake_client(monkeypatch, controller, no_sleep):
    """Patch the CLI so every command runs against FakeController."""
    holder = {"client": FakeClient(controller)}
    monkeypatch.setattr("pentair_cli.cli.IntelliCenterClient", lambda **kw: holder["client"])
    return holder
