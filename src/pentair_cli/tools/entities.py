"""Entity listing / lookup tools (bodies, circuits, lights, raw objects)."""

from __future__ import annotations

from typing import Any

from pentair_cli.client import IntelliCenterClient
from pentair_cli.models.schemas import (
    CircuitStateResult,
    Light,
    LightEffect,
    LightEffectResult,
    ObjectDetail,
    Ref,
)
from pentair_cli.models.vocabulary import is_system_object
from pentair_cli.tools import AmbiguousNameError, NotFoundError
from pentair_cli.tools.common import object_ref, ref_fields, resolve


def user_circuits(controller: Any) -> list[Any]:
    return [c for c in controller.get_circuits() if not is_system_object(c.objnam)]


def resolve_circuit(controller: Any, ident: str) -> Any:
    """Prefer circuits a user would see; fall back to virtual/system ones."""
    try:
        return resolve(user_circuits(controller), ident, "circuit")
    except AmbiguousNameError:
        raise
    except NotFoundError:
        return resolve(controller.get_circuits(), ident, "circuit")


async def list_bodies(client: IntelliCenterClient) -> list[Ref]:
    async with client.session() as controller:
        return [object_ref(b) for b in controller.get_bodies()]


async def list_circuits(client: IntelliCenterClient, include_system: bool = False) -> list[Ref]:
    async with client.session() as controller:
        circuits = controller.get_circuits() if include_system else user_circuits(controller)
        return [object_ref(c) for c in circuits]


def _light(controller: Any, obj: Any) -> Light:
    effect = None
    if getattr(obj, "supports_color_effects", False):
        try:
            effect = controller.get_light_effect_name(obj.objnam)
        except Exception:
            effect = None
    return Light(**ref_fields(obj), effect=effect)


async def list_lights(client: IntelliCenterClient) -> list[Light]:
    async with client.session() as controller:
        return [_light(controller, obj) for obj in controller.get_lights()]


async def list_entities(
    client: IntelliCenterClient, kind: str | None = None
) -> dict[str, list[Ref]]:
    async with client.session() as controller:
        entities = controller.get_all_entities()
        if kind is not None:
            key = kind.replace(" ", "_").replace("-", "_").lower()
            if key not in entities:
                valid = ", ".join(entities)
                raise NotFoundError(f"Unknown entity kind '{kind}'. Valid kinds: {valid}")
            entities = {key: entities[key]}
        return {k: [object_ref(e) for e in items] for k, items in entities.items()}


async def get_object(client: IntelliCenterClient, ident: str) -> ObjectDetail:
    """Get details for an object by ID or name."""
    async with client.session() as controller:
        obj = resolve(controller.model.objects.values(), ident, "object")
        attrs = dict(getattr(obj, "properties", {}) or {})
        return ObjectDetail(**ref_fields(obj), attributes=attrs)


async def set_circuit_state(
    client: IntelliCenterClient, ident: str, on: bool
) -> CircuitStateResult:
    """Turn a circuit on/off. Accepts ID or name."""
    async with client.session() as controller:
        circuit = resolve_circuit(controller, ident)
        await controller.set_circuit_state(circuit.objnam, on)
        return CircuitStateResult(id=circuit.objnam, name=getattr(circuit, "sname", None), on=on)


def available_light_effects() -> list[LightEffect]:
    from pyintellicenter import ICModelController

    return [
        LightEffect(name=name, code=code)
        for code, name in ICModelController.get_available_light_effects().items()
    ]


def resolve_effect(effect: str) -> LightEffect:
    """Accept an effect name (Party Mode) or code (PARTY), case-insensitive."""
    wanted = effect.strip().lower()
    for e in available_light_effects():
        if wanted in (e.code.lower(), e.name.lower()):
            return e
    valid = ", ".join(f"{e.name} ({e.code})" for e in available_light_effects())
    raise NotFoundError(f"Unknown light effect '{effect}'. Valid effects: {valid}")


async def set_light_effect(
    client: IntelliCenterClient, ident: str, effect: str
) -> LightEffectResult:
    """Set light effect for a light circuit. Accepts ID or name."""
    chosen = resolve_effect(effect)
    async with client.session() as controller:
        light = resolve(controller.get_lights(), ident, "light")
        await controller.set_light_effect(light.objnam, chosen.code)
        return LightEffectResult(
            id=light.objnam,
            name=getattr(light, "sname", None),
            effect=chosen.name,
            effect_code=chosen.code,
        )
