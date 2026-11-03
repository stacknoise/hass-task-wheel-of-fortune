"""Plattform `button`: Home Assistant sucht sie hier, die Umsetzung liegt in `entities/`."""

from .entities.button import async_setup_entry

__all__ = ["async_setup_entry"]
