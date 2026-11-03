"""Kennungen für neue Runden, Zuteilungen und Panel-Runden."""

from uuid import uuid4


def new_id() -> str:
    """Neue zufällige Kennung (32 Hexzeichen)."""
    return uuid4().hex
