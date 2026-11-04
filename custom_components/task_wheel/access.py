"""Zugriffsrecht für Dienste, Button und To-do-Liste: dasselbe wie bei den WebSocket-Befehlen."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.exceptions import Unauthorized

if TYPE_CHECKING:
    from homeassistant.core import Context, HomeAssistant


async def ensure_allowed(hass: HomeAssistant, context: Context | None, *, admin_only: bool) -> None:
    """Bei „Panel nur für Administratoren“ dürfen auch Aktionen nur Administratoren auslösen.

    Aufrufe ohne Benutzer (Automationen, System) bleiben erlaubt; ein Benutzer, den es nicht
    mehr gibt, nicht.

    Raises:
        Unauthorized: Der Benutzer ist kein Administrator.
    """
    if not admin_only or context is None or context.user_id is None:
        return
    user = await hass.auth.async_get_user(context.user_id)
    if user is None or not user.is_admin:
        raise Unauthorized(context=context)
