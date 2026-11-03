"""Elemente über eine Referenz finden (Kennung, Kurzname oder Name), z. B. aus Diensten."""

from collections.abc import Callable, Iterable

from ..domain.errors import NotFoundError


def find_by_ref[T](
    items: Iterable[T], ref: str, resource: str, keys: Callable[[T], Iterable[str]]
) -> T:
    """Liefert das erste Element, dessen Schlüssel `ref` entspricht.

    Raises:
        NotFoundError: Kein Element passt.
    """
    for item in items:
        if ref in keys(item):
            return item
    raise NotFoundError(resource, ref)
