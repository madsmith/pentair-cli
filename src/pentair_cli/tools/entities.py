"""Entity listing / lookup tools (bodies, circuits, lights, raw objects)."""

from __future__ import annotations

from pentair_cli.client import IntelliCenterClient
from pentair_cli.models.schemas import (
    CircuitStateResult,
    LightEffect,
    LightEffectResult,
    ObjectDetail,
    ObjectRef,
)
from pentair_cli.tools import NotFoundError
from pentair_cli.tools.common import object_ref, resolve


async def list_bodies(client: IntelliCenterClient) -> list[ObjectRef]:
    async with client.session() as controller:
        return [object_ref(b) for b in controller.get_bodies()]


async def list_circuits(client: IntelliCenterClient) -> list[ObjectRef]:
    async with client.session() as controller:
        return [object_ref(c) for c in controller.get_circuits()]


async def list_lights(client: IntelliCenterClient) -> list[ObjectRef]:
    async with client.session() as controller:
        return [object_ref(light) for light in controller.get_lights()]


async def list_entities(
    client: IntelliCenterClient, kind: str | None = None
) -> dict[str, list[ObjectRef]]:
    async with client.session() as controller:
        entities = controller.get_all_entities()
        if kind is not None:
            if kind not in entities:
                raise NotFoundError(
                    f"Unknown entity kind '{kind}'. Valid kinds: {', '.join(entities)}"
                )
            entities = {kind: entities[kind]}
        return {k: [object_ref(e) for e in items] for k, items in entities.items()}


async def get_object(client: IntelliCenterClient, ident: str) -> ObjectDetail:
    """Get details for an object by objnam or sname."""
    async with client.session() as controller:
        obj = resolve(controller.model.objects.values(), ident, "object")
        ref = object_ref(obj)
        props = dict(getattr(obj, "properties", {}) or {})
        return ObjectDetail(**ref.model_dump(), properties=props)


async def set_circuit_state(
    client: IntelliCenterClient, ident: str, state: bool
) -> CircuitStateResult:
    """Turn a circuit on/off. Accepts objnam or sname."""
    async with client.session() as controller:
        circuit = resolve(controller.get_circuits(), ident, "circuit")
        await controller.set_circuit_state(circuit.objnam, state)
        return CircuitStateResult(objnam=ident, resolved_objnam=circuit.objnam, state=state)


def available_light_effects() -> list[LightEffect]:
    from pyintellicenter import ICModelController

    return [
        LightEffect(code=code, name=name)
        for code, name in ICModelController.get_available_light_effects().items()
    ]


def resolve_effect(effect: str) -> LightEffect:
    """Accept an effect code (PARTY) or display name (Party Mode), case-insensitive."""
    wanted = effect.strip().lower()
    for e in available_light_effects():
        if wanted in (e.code.lower(), e.name.lower()):
            return e
    valid = ", ".join(f"{e.code} ({e.name})" for e in available_light_effects())
    raise NotFoundError(f"Unknown light effect '{effect}'. Valid effects: {valid}")


async def set_light_effect(
    client: IntelliCenterClient, ident: str, effect: str
) -> LightEffectResult:
    """Set light effect for a light circuit. Accepts objnam or sname."""
    chosen = resolve_effect(effect)
    async with client.session() as controller:
        light = resolve(controller.get_lights(), ident, "light")
        await controller.set_light_effect(light.objnam, chosen.code)
        return LightEffectResult(
            objnam=ident, resolved_objnam=light.objnam, effect=chosen.code, effect_name=chosen.name
        )
