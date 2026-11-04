"""Elemente über eine Referenz finden (Kennung, Kurzname oder Name), z. B. aus Diensten."""

from collections.abc import Callable, Iterable

from ..domain.errors import AmbiguousReferenceError, NotFoundError


def find_by_ref[T](
    items: Iterable[T], ref: str, resource: str, keys: Callable[[T], Iterable[str]]
) -> T:
    """Liefert das Element, dessen Schlüssel `ref` entspricht.

    Raises:
        NotFoundError: Kein Element passt.
        AmbiguousReferenceError: Mehrere Elemente passen (z. B. zwei Aufgaben desselben Namens).
    """
    found = [item for item in items if ref in keys(item)]
    if not found:
        raise NotFoundError(resource, ref)
    if len(found) > 1:
        raise AmbiguousReferenceError(resource, ref)
    return found[0]
