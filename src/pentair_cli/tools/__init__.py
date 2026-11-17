"""IntelliCenter operations.

Each module exposes:

* ``read_*`` / ``apply_*`` functions that take an already-connected controller
  (so several reads can share one connection, e.g. ``pentair-cli status``), and
* ``get_*`` / ``set_*`` wrappers that take an ``IntelliCenterClient`` and open
  their own session — the same shape as the pentair-mcp ``tools`` package.
"""


class NotFoundError(LookupError):
    """Raised when a named body/circuit/light/object does not exist."""


class AmbiguousNameError(NotFoundError):
    """Raised when a display name matches more than one object."""
