"""Schwellwertprüfung (`--check`): sammelt Messwerte je Bereich und meldet rote Werte."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import (
    LAYER_DOMAIN,
    SCOPE_DOMAIN_INSTABILITY,
    SCOPE_METHOD_CC,
    SCOPE_METHOD_LOC,
    SCOPE_MODULE_LOC,
    SCOPE_MODULE_MI,
    STATUS_RED,
)
from .models import Finding

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from .models import MethodInfo, ModuleInfo, Report
    from .thresholds import Threshold

type Measurement = tuple[str, float]


def _methods(report: Report) -> Iterator[tuple[str, MethodInfo]]:
    """Alle Methoden und Funktionen mit Fundstelle `pfad:zeile name`."""
    for module in report.modules:
        for method in (*module.functions, *(m for t in module.types for m in t.methods)):
            yield f"{module.path}:{method.line_start} {method.name}", method


def _per_module(report: Report, getter: Callable[[ModuleInfo], float]) -> Iterator[Measurement]:
    """Ein Messwert je Modul."""
    return ((module.path, getter(module)) for module in report.modules)


MEASUREMENTS: dict[str, Callable[[Report], Iterator[Measurement]]] = {
    SCOPE_METHOD_CC: lambda r: ((where, m.metrics.cc) for where, m in _methods(r)),
    SCOPE_METHOD_LOC: lambda r: ((where, m.metrics.loc) for where, m in _methods(r)),
    SCOPE_MODULE_MI: lambda r: _per_module(r, lambda m: m.metrics.mi),
    SCOPE_MODULE_LOC: lambda r: _per_module(r, lambda m: m.metrics.loc),
    SCOPE_DOMAIN_INSTABILITY: lambda r: (
        (m.path, m.instability) for m in r.modules if m.layer == LAYER_DOMAIN
    ),
}


def find_violations(report: Report, thresholds: tuple[Threshold, ...]) -> list[Finding]:
    """Alle Messwerte im roten Bereich."""
    return [
        Finding(location, threshold.scope, value, threshold.red)
        for threshold in thresholds
        for location, value in MEASUREMENTS[threshold.scope](report)
        if threshold.status(value) == STATUS_RED
    ]
