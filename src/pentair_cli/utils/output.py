"""Rendering results as human-readable text or JSON."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from pydantic import BaseModel


def to_jsonable(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, Mapping):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [to_jsonable(v) for v in obj]
    return obj


def render_json(obj: Any) -> str:
    return json.dumps(to_jsonable(obj), indent=2, default=str, ensure_ascii=False)


def fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, list | tuple):
        return ", ".join(fmt(v) for v in value) or "-"
    if isinstance(value, Mapping):
        return ", ".join(f"{k}={fmt(v)}" for k, v in value.items()) or "-"
    return str(value)


def kv(data: Mapping[str, Any] | BaseModel, title: str | None = None, indent: int = 0) -> str:
    if isinstance(data, BaseModel):
        data = data.model_dump()
    pad = " " * indent
    lines = [f"{pad}{title}"] if title else []
    inner = pad + ("  " if title else "")
    width = max((len(k) for k in data), default=0)
    for key, value in data.items():
        lines.append(f"{inner}{key.ljust(width)}  {fmt(value)}")
    return "\n".join(lines)


def table(rows: Iterable[Mapping[str, Any] | BaseModel], columns: Sequence[str]) -> str:
    materialized = [r.model_dump() if isinstance(r, BaseModel) else dict(r) for r in rows]
    if not materialized:
        return "(none)"
    cells = [[fmt(r.get(c)) for c in columns] for r in materialized]
    widths = [max(len(c), *(len(row[i]) for row in cells)) for i, c in enumerate(columns)]
    header = "  ".join(c.upper().ljust(w) for c, w in zip(columns, widths, strict=True))
    body = [
        "  ".join(v.ljust(w) for v, w in zip(row, widths, strict=True)).rstrip() for row in cells
    ]
    return "\n".join([header.rstrip(), *body])


def temp(value: Any, unit: str | None) -> str:
    return "-" if value is None else f"{fmt(value)}°{unit or ''}"
