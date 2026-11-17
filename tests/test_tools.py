"""Tests for tool logic against a fake controller."""

from __future__ import annotations

import pytest

from pentair_cli.tools import AmbiguousNameError, NotFoundError, entities, pool, spa, system
from pentair_cli.tools.body import apply_body_setpoint, convert
from pentair_cli.tools.common import resolve
from tests.conftest import FakeClient, FakeController


def test_resolve_objnam_then_sname_case_insensitive(controller):
    assert resolve(controller.circuits, "C0003", "circuit").objnam == "C0003"
    assert resolve(controller.circuits, "jets", "circuit").objnam == "C0003"


def test_resolve_ambiguous_and_missing(controller):
    with pytest.raises(AmbiguousNameError, match="C0015, X0043"):
        resolve(controller.circuits, "cleaner", "circuit")
    with pytest.raises(NotFoundError, match="Known circuits: Cleaner, Jets, Spa"):
        resolve(controller.circuits, "nope", "circuit")


async def test_pool_and_spa_status(controller):
    client = FakeClient(controller)
    p = await pool.get_pool_status(client)
    assert (p.body, p.temperature, p.setpoint, p.pump_speed, p.unit) == ("B1101", 56, 55, 3000, "F")
    s = await spa.get_spa_status(client)
    assert (s.body, s.temperature, s.heater_on) == ("B1202", 78, False)


async def test_overview(controller):
    ov = await system.get_overview(FakeClient(controller))
    assert ov.system.prop_name == "Test"
    assert [c.objnam for c in ov.circuits_on] == ["C0001"]


async def test_setpoint_native_unit(controller, no_sleep):
    r = await apply_body_setpoint(controller, "SPA", 101.6)
    assert (r.temperature, r.unit, r.verified) == (102, "F", True)
    assert ("setpoint", "B1202", 102) in controller.calls
    assert controller.calls[0][0] == "heat_mode"


async def test_setpoint_converts_units(no_sleep):
    metric = FakeController(metric=True)
    r = await apply_body_setpoint(metric, "pool", 84, unit="F")
    assert (r.temperature, r.unit, r.requested_unit) == (29, "C", "F")


async def test_setpoint_out_of_range(controller, no_sleep):
    with pytest.raises(ValueError, match="safe range"):
        await apply_body_setpoint(controller, "spa", 120)
    assert controller.calls == []


def test_convert():
    assert convert(212, "F", "C") == pytest.approx(100)
    assert convert(0, "C", "F") == pytest.approx(32)


def test_resolve_effect():
    assert entities.resolve_effect("party").code == "PARTY"
    assert entities.resolve_effect("Party Mode").code == "PARTY"
    with pytest.raises(NotFoundError):
        entities.resolve_effect("disco")


async def test_circuit_and_light_writes(controller):
    client = FakeClient(controller)
    r = await entities.set_circuit_state(client, "jets", True)
    assert r.resolved_objnam == "C0003" and ("circuit", "C0003", True) in controller.calls
    r = await entities.set_light_effect(client, "pool lights", "caribbean")
    assert r.effect == "CARIB" and ("effect", "C0009", "CARIB") in controller.calls


async def test_entity_kind_filter_and_get(controller):
    client = FakeClient(controller)
    assert list(await entities.list_entities(client, "lights")) == ["lights"]
    with pytest.raises(NotFoundError, match="Valid kinds"):
        await entities.list_entities(client, "dragons")
    d = await entities.get_object(client, "B1101")
    assert d.properties["SNAME"] == "Pool"
