"""Helpers shared across tools."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pentair_cli.models.schemas import Ref
from pentair_cli.models.vocabulary import kind_label, on_state, type_label
from pentair_cli.tools import AmbiguousNameError, NotFoundError

MAX_HINT_NAMES = 30


def ref_fields(obj: Any) -> dict[str, Any]:
    return {
        "id": obj.objnam,
        "name": getattr(obj, "sname", None),
        "kind": kind_label(getattr(obj, "objtype", None)),
        "type": type_label(getattr(obj, "subtype", None)),
        "on": on_state(getattr(obj, "status", None)),
    }


def object_ref(obj: Any) -> Ref:
    return Ref(**ref_fields(obj))


def resolve(candidates: Iterable[Any], ident: str, kind: str) -> Any:
    """Find an object by exact ID, then case-insensitive name."""
    items = list(candidates)
    for obj in items:
        if obj.objnam == ident:
            return obj
    lowered = ident.lower()
    matches = [o for o in items if (getattr(o, "sname", None) or "").lower() == lowered]
    if len(matches) == 1:
        return matches[0]
    if matches:
        ids = ", ".join(o.objnam for o in matches)
        raise AmbiguousNameError(f"'{ident}' matches several {kind}s ({ids}); use the ID instead.")
    known = sorted({s for o in items if (s := getattr(o, "sname", None)) and s.isprintable()})
    if len(known) > MAX_HINT_NAMES:
        hint = f" {len(known)} {kind}s exist; list them to find the right name."
    elif known:
        hint = f" Known {kind}s: {', '.join(known)}"
    else:
        hint = ""
    raise NotFoundError(f"No {kind} named '{ident}'.{hint}")
