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


def test_resolve_hint_is_capped():
    from types import SimpleNamespace

    many = [SimpleNamespace(objnam=f"C{i:04}", sname=f"Circuit {i}") for i in range(40)]
    with pytest.raises(NotFoundError, match="40 objects exist; list them") as e:
        resolve(many, "nope", "object")
    assert "Circuit 1" not in str(e.value)


def test_resolve_ambiguous_and_missing(controller):
    with pytest.raises(AmbiguousNameError, match="C0015, X0043.*use the ID"):
        resolve(controller.circuits, "cleaner", "circuit")
    with pytest.raises(NotFoundError, match="Known circuits: All Lights On, Cleaner, Jets"):
        resolve(controller.circuits, "nope", "circuit")


async def test_pool_and_spa_status(controller):
    client = FakeClient(controller)
    p = await pool.get_pool_status(client)
    assert (p.id, p.temperature, p.setpoint, p.pump_rpm, p.unit) == ("B1101", 56, 55, 3000, "F")
    s = await spa.get_spa_status(client)
    assert (s.id, s.temperature, s.heating) == ("B1202", 78, False)
    # Mode Off: no heat source reported even though a heater is assigned.
    assert (s.heat_mode, s.heat_source) == ("Off", None)
    assert (p.heat_mode, p.heat_source, p.heat_source_id) == ("Heater", "Gas Heater", "H0001")


def test_heat_mode_names():
    from pyintellicenter import HeaterType

    from pentair_cli.tools.body import heat_mode_name

    assert heat_mode_name(HeaterType.SOLAR_PREFERRED) == "Solar Preferred"
    assert heat_mode_name(HeaterType.ULTRA_TEMP_PREFERRED) == "UltraTemp Preferred"
    assert heat_mode_name(None) is None


async def test_overview(controller):
    ov = await system.get_overview(FakeClient(controller))
    assert (ov.system.name, ov.system.firmware, ov.system.unit) == ("Test", "3.008", "F")
    assert [c.id for c in ov.circuits_on] == ["C0001"]


async def test_setpoint_native_unit(controller, no_sleep):
    r = await apply_body_setpoint(controller, "SPA", 101.6)
    assert (r.setpoint, r.unit, r.confirmed, r.name) == (102, "F", True, "Spa")
    assert ("setpoint", "B1202", 102) in controller.calls
    assert controller.calls[0][0] == "heat_mode"


async def test_setpoint_converts_units(no_sleep):
    metric = FakeController(metric=True)
    r = await apply_body_setpoint(metric, "pool", 84, unit="F")
    assert (r.setpoint, r.unit, r.requested_unit) == (29, "C", "F")


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
    assert (r.id, r.name, r.on) == ("C0003", "Jets", True)
    assert ("circuit", "C0003", True) in controller.calls
    r = await entities.set_light_effect(client, "pool lights", "caribbean")
    assert (r.effect, r.effect_code) == ("Caribbean", "CARIB")
    assert ("effect", "C0009", "CARIB") in controller.calls


async def test_circuit_name_prefers_user_circuits(controller):
    client = FakeClient(controller)
    # "Cleaner" is also a virtual X-series circuit; the real one wins.
    r = await entities.set_circuit_state(client, "Cleaner", True)
    assert r.id == "C0015"
    # System circuits are still reachable by ID or by a name only they have.
    assert (await entities.set_circuit_state(client, "X0043", False)).id == "X0043"
    assert (await entities.set_circuit_state(client, "all lights on", True)).id == "_A111"
    with pytest.raises(AmbiguousNameError, match="C0016, C0017"):
        await entities.set_circuit_state(client, "step light", True)


async def test_circuit_list_hides_system_by_default(controller):
    client = FakeClient(controller)
    ids = [r.id for r in await entities.list_circuits(client)]
    assert "X0043" not in ids and "_A111" not in ids and "C0015" in ids
    all_ids = [r.id for r in await entities.list_circuits(client, include_system=True)]
    assert {"X0043", "_A111"} <= set(all_ids)


def test_ref_vocabulary(controller):
    from pentair_cli.tools.common import object_ref

    r = object_ref(controller.lights[0])
    assert r.model_dump() == {
        "id": "C0009",
        "name": "Pool Lights",
        "kind": "circuit",
        "type": "IntelliBrite light",
        "on": False,
    }
    assert object_ref(controller.circuits[3]).type == "Virtual"
    assert object_ref(controller.circuits[4]).on is None  # PERMIT


async def test_model_summary_uses_plural_kinds(controller):
    s = await system.get_model_summary(FakeClient(controller))
    assert s.by_kind["circuits"] == 8 and s.by_kind["bodies"] == 2
    assert s.total == sum(s.by_kind.values())


async def test_entity_kind_filter_and_get(controller):
    client = FakeClient(controller)
    assert list(await entities.list_entities(client, "lights")) == ["lights"]
    with pytest.raises(NotFoundError, match="Valid kinds"):
        await entities.list_entities(client, "dragons")
    d = await entities.get_object(client, "B1101")
    assert (d.id, d.name, d.kind) == ("B1101", "Pool", "body")
    assert d.attributes["SNAME"] == "Pool"
