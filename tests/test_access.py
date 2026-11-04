"""Zugriffsrecht der Dienste und Entitäten (`access`) und Übersetzung von Fachfehlern."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import Unauthorized

from custom_components.task_wheel.access import ensure_allowed
from custom_components.task_wheel.domain.errors import NotFoundError
from custom_components.task_wheel.service_errors import to_service_error, to_setup_error


def _hass(*, is_admin: bool | None) -> MagicMock:
    """Home Assistant mit einem Benutzer (`None`: Benutzer unbekannt)."""
    hass = MagicMock()
    user = None if is_admin is None else SimpleNamespace(is_admin=is_admin)
    hass.auth.async_get_user = AsyncMock(return_value=user)
    return hass


async def test_everyone_may_act_without_the_restriction() -> None:
    hass = _hass(is_admin=False)
    await ensure_allowed(hass, SimpleNamespace(user_id="u1"), admin_only=False)
    hass.auth.async_get_user.assert_not_awaited()


async def test_calls_without_a_user_stay_allowed() -> None:
    hass = _hass(is_admin=False)
    await ensure_allowed(hass, SimpleNamespace(user_id=None), admin_only=True)
    await ensure_allowed(hass, None, admin_only=True)
    hass.auth.async_get_user.assert_not_awaited()


async def test_administrators_may_act_with_the_restriction() -> None:
    await ensure_allowed(_hass(is_admin=True), SimpleNamespace(user_id="u1"), admin_only=True)


@pytest.mark.parametrize("is_admin", [False, None])
async def test_other_users_are_rejected_with_the_restriction(is_admin: bool | None) -> None:
    context = SimpleNamespace(user_id="u1")
    with pytest.raises(Unauthorized):
        await ensure_allowed(_hass(is_admin=is_admin), context, admin_only=True)


def test_domain_errors_become_translatable_errors() -> None:
    err = NotFoundError("person", "p9")
    service = to_service_error(err)
    setup = to_setup_error(err)
    for translated in (service, setup):
        assert translated.translation_key == "not_found"
        assert translated.translation_placeholders == {"resource": "person", "id": "p9"}
