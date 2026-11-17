"""Translate IntelliCenter codes into the CLI's user-facing vocabulary.

This is the only place that should know IntelliCenter's names for things
(``CIRCUIT``, ``INTELLI``, ``CIRCGRP``...). Everything the CLI prints uses the
words defined here.
"""

from __future__ import annotations

# objtype -> (singular kind, plural kind)
KINDS: dict[str, tuple[str, str]] = {
    "BODY": ("body", "bodies"),
    "CHEM": ("chemistry controller", "chemistry controllers"),
    "CIRCGRP": ("circuit group member", "circuit group members"),
    "CIRCUIT": ("circuit", "circuits"),
    "EXTINSTR": ("external instrument", "external instruments"),
    "FEATR": ("feature", "features"),
    "HEATER": ("heater", "heaters"),
    "MODULE": ("module", "modules"),
    "PANEL": ("panel", "panels"),
    "PERMIT": ("permit", "permits"),
    "PMPCIRC": ("pump circuit", "pump circuits"),
    "PRESS": ("pressure sensor", "pressure sensors"),
    "PUMP": ("pump", "pumps"),
    "REMBTN": ("remote button", "remote buttons"),
    "REMOTE": ("remote", "remotes"),
    "SCHED": ("schedule", "schedules"),
    "SENSE": ("sensor", "sensors"),
    "SYSTEM": ("system", "system"),
    "SYSTIM": ("clock", "clocks"),
    "VALVE": ("valve", "valves"),
}

# subtype -> human label. Keys are upper-cased before lookup, except the
# lower-case "Generic" IntelliCenter uses for virtual (X-series) circuits.
TYPES: dict[str, str] = {
    "Generic": "Virtual",
    "GENERIC": "Generic",
    "POOL": "Pool",
    "SPA": "Spa",
    "LIGHT": "Light",
    "INTELLI": "IntelliBrite light",
    "MAGIC2": "MagicStream light",
    "CLRCASC": "Color cascade light",
    "DIMMER": "Dimmer light",
    "GLOW": "GloBrite light",
    "GLOWT": "GloBrite White light",
    "PHOTON": "Photon light",
    "SAML": "SAm/SAL light",
    "COLORW": "Color wheel light",
    "LITSHO": "Light show",
    "CIRCGRP": "Group",
    "FRZ": "Freeze protection",
    "ALL": "All lights",
    "MASTER": "Master cleaner",
    "CHEM": "Chemistry",
    "ULTRA": "UltraTemp heat pump",
    "HCOMBO": "Hybrid heater",
    "SOLAR": "Solar",
    "HTPMP": "Heat pump",
    "SPEED": "Single speed",
    "VS": "Variable speed",
    "VF": "Variable flow",
    "VSF": "Variable speed/flow",
}


def kind_label(objtype: str | None, plural: bool = False) -> str | None:
    if not objtype:
        return None
    names = KINDS.get(objtype.upper())
    if names is None:
        return objtype.lower()
    return names[1] if plural else names[0]


def type_label(subtype: str | None) -> str | None:
    if not subtype:
        return None
    if subtype in TYPES:
        return TYPES[subtype]
    return TYPES.get(subtype.upper(), subtype.replace("_", " ").title())


def on_state(status: str | None) -> bool | None:
    """IntelliCenter STATUS -> True/False, None when it isn't an on/off value."""
    if status == "ON":
        return True
    if status == "OFF":
        return False
    return None


def is_system_object(objnam: str) -> bool:
    """Virtual (X-series) and system (_-prefixed) circuits the app doesn't show."""
    return objnam.startswith(("X", "_"))
