"""Messgrößen: LOC, Halstead-Volumen, Wartbarkeitsindex, Instabilität."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .constants import (
    INSTABILITY_DIGITS,
    KIND_NAME,
    KIND_OP,
    MI_CC_WEIGHT,
    MI_DIGITS,
    MI_EMPTY,
    MI_LOC_WEIGHT,
    MI_OFFSET,
    MI_SCALE,
    MI_VOLUME_WEIGHT,
    MIN_VOCABULARY,
)
from .models import Metrics

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .models import Token


def code_lines(tokens: Sequence[Token]) -> int:
    """Zählt die Zeilen, die mindestens ein Token tragen (ohne Leerzeilen und Kommentare)."""
    lines: set[int] = set()
    for token in tokens:
        lines.update(range(token.line, token.end_line + 1))
    return len(lines)


def halstead_volume(tokens: Sequence[Token], keywords: frozenset[str]) -> float:
    """Berechnet das Halstead-Volumen `N · log2(n)` über Operatoren und Operanden."""
    symbols = [
        (token.kind == KIND_OP or (token.kind == KIND_NAME and token.text in keywords), token.text)
        for token in tokens
    ]
    vocabulary = len(set(symbols))
    if vocabulary < MIN_VOCABULARY:
        return 0.0
    return len(symbols) * math.log2(vocabulary)


def maintainability(volume: float, cc: int, loc: int) -> float:
    """Wartbarkeitsindex 0 bis 100 nach CODE_DOKU.md §1."""
    if loc <= 0:
        return MI_EMPTY
    raw = (
        MI_OFFSET
        - MI_VOLUME_WEIGHT * math.log(max(volume, 1.0))
        - MI_CC_WEIGHT * cc
        - MI_LOC_WEIGHT * math.log(loc)
    )
    return round(max(0.0, raw * MI_SCALE / MI_OFFSET), MI_DIGITS)


def build_metrics(tokens: Sequence[Token], cc: int, keywords: frozenset[str]) -> Metrics:
    """Fasst die Messwerte eines Token-Abschnitts zusammen."""
    loc = code_lines(tokens)
    volume = halstead_volume(tokens, keywords)
    return Metrics(loc=loc, cc=cc, mi=maintainability(volume, cc, loc))


def instability(ca: int, ce: int) -> float:
    """Instabilität `Ce / (Ca + Ce)`; 0 bei isolierten Elementen."""
    total = ca + ce
    return round(ce / total, INSTABILITY_DIGITS) if total else 0.0


def weighted_maintainability(parts: Sequence[Metrics]) -> float | None:
    """LOC-gewichteter Mittelwert der Wartbarkeitsindizes; `None` ohne Teile mit Code."""
    weight = sum(part.loc for part in parts)
    if not weight:
        return None
    return round(sum(part.mi * part.loc for part in parts) / weight, MI_DIGITS)
