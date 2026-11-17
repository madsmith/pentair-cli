"""Helpers shared across tools."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pentair_cli.models.schemas import ObjectRef
from pentair_cli.tools import AmbiguousNameError, NotFoundError


def object_ref(obj: Any) -> ObjectRef:
    return ObjectRef(
        objnam=obj.objnam,
        sname=getattr(obj, "sname", None),
        type=getattr(obj, "objtype", None),
        subtype=getattr(obj, "subtype", None),
        status=getattr(obj, "status", None),
    )


def resolve(candidates: Iterable[Any], ident: str, kind: str) -> Any:
    """Find an object by exact objnam, then case-insensitive sname."""
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
        raise AmbiguousNameError(
            f"'{ident}' matches several {kind}s ({ids}); use the objnam instead."
        )
    names = ", ".join(sorted({s for o in items if (s := getattr(o, "sname", None))}))
    hint = f" Known {kind}s: {names}" if names else ""
    raise NotFoundError(f"No {kind} named '{ident}'.{hint}")
