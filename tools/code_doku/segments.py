"""Gemeinsame Bausteine der Scanner: Token-Abschnitte, Quelltext-Auszüge, Element-Bau."""

from __future__ import annotations

import textwrap
from bisect import bisect_left, bisect_right
from dataclasses import replace
from typing import TYPE_CHECKING

from .constants import KIND_NAME, NEWLINE
from .metrics import build_metrics, weighted_maintainability
from .models import MethodInfo, Metrics, TypeInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .models import Token


class Source:
    """Quelltext mit Token-Index für Zugriffe nach Zeilenbereich."""

    def __init__(self, text: str, tokens: Sequence[Token], keywords: frozenset[str]) -> None:
        """Merkt Text, Tokens (nach Zeile sortiert) und die Schlüsselwörter der Sprache."""
        self.lines = text.split(NEWLINE)
        self.tokens = tokens
        self.keywords = keywords
        self._starts = [token.line for token in tokens]

    def tokens_between(self, line_start: int, line_end: int) -> Sequence[Token]:
        """Tokens, die in den Zeilen `line_start..line_end` beginnen."""
        low = bisect_left(self._starts, line_start)
        high = bisect_right(self._starts, line_end)
        return self.tokens[low:high]

    def text_between(self, line_start: int, line_end: int) -> str:
        """Eingerückten Quelltext der Zeilen `line_start..line_end` liefern."""
        return textwrap.dedent(NEWLINE.join(self.lines[line_start - 1 : line_end]))

    def metrics_between(self, line_start: int, line_end: int, cc: int) -> Metrics:
        """Messwerte des Zeilenbereichs bei gegebener Komplexität."""
        return build_metrics(self.tokens_between(line_start, line_end), cc, self.keywords)

    def method(  # noqa: PLR0917
        self,
        name: str,
        kind: str,
        signature: str,
        doc: str,
        bounds: tuple[int, int],
        cc: int,
    ) -> MethodInfo:
        """Baut eine `MethodInfo` für den Zeilenbereich `bounds`."""
        start, end = bounds
        return MethodInfo(
            name=name,
            kind=kind,
            signature=signature,
            doc=doc,
            line_start=start,
            line_end=end,
            metrics=self.metrics_between(start, end, cc),
            source=self.text_between(start, end),
        )

    def type_info(
        self,
        name: str,
        kind: str,
        doc: str,
        bounds: tuple[int, int],
        methods: tuple[MethodInfo, ...],
    ) -> TypeInfo:
        """Baut eine `TypeInfo`; die Komplexität ist die Summe der Methoden."""
        start, end = bounds
        cc = sum(method.metrics.cc for method in methods)
        return TypeInfo(
            name=name,
            kind=kind,
            doc=doc,
            line_start=start,
            line_end=end,
            metrics=self.metrics_between(start, end, cc),
            methods=methods,
            refs=self.names_between(start, end),
        )

    def names_between(self, line_start: int, line_end: int) -> frozenset[str]:
        """Alle Bezeichner (ohne Schlüsselwörter) im Zeilenbereich."""
        return frozenset(
            token.text
            for token in self.tokens_between(line_start, line_end)
            if token.kind == KIND_NAME and token.text not in self.keywords
        )


def module_metrics(
    tokens: Sequence[Token],
    methods: Sequence[MethodInfo],
    keywords: frozenset[str],
) -> Metrics:
    """Modul-Messwerte; der MI ist der LOC-gewichtete Mittelwert der Methoden, falls vorhanden."""
    raw = build_metrics(tokens, sum(method.metrics.cc for method in methods), keywords)
    mi = weighted_maintainability([method.metrics for method in methods])
    return raw if mi is None else replace(raw, mi=mi)
