"""Ziele erkennen, Versandarten, Fabrik, Texte (Home Assistant wird nachgebildet)."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.task_wheel.const import notification as c
from custom_components.task_wheel.domain.enums import NotifyTargetKind
from custom_components.task_wheel.domain.errors import (
    InvalidNotifyTargetError,
    NotifyFailedError,
)
from custom_components.task_wheel.infrastructure.notifier.factory import NotifierFactory
from custom_components.task_wheel.infrastructure.notifier.hass_notifier import HassNotifier
from custom_components.task_wheel.infrastructure.notifier.senders import (
    EntitySender,
    NoSender,
    ServiceSender,
)
from custom_components.task_wheel.infrastructure.notifier.target import classify
from custom_components.task_wheel.infrastructure.notifier.texts import load_catalog

TEXTS = Path(__file__).parents[2] / "custom_components" / "task_wheel" / c.TEXTS_DIRECTORY


def make_hass(entities: tuple[str, ...] = (), services: tuple[str, ...] = ()) -> MagicMock:
    hass = MagicMock()
    hass.states.get.side_effect = lambda entity: object() if entity in entities else None
    hass.services.has_service.side_effect = lambda domain, name: (
        domain == "notify" and name in services
    )
    hass.services.async_call = AsyncMock()
    return hass


@pytest.mark.parametrize(
    ("target", "kind"),
    [
        ("notify.anna", NotifyTargetKind.NOTIFY_ENTITY),
        ("notify.mobile", NotifyTargetKind.NOTIFY_SERVICE),
        ("notify.nothing", NotifyTargetKind.NONE),
        ("notify.send_message", NotifyTargetKind.NONE),
        ("light.kitchen", NotifyTargetKind.NONE),
        ("notify.a b", NotifyTargetKind.NONE),
        ("notify.", NotifyTargetKind.NONE),
        ("", NotifyTargetKind.NONE),
    ],
)
def test_classify(target: str, kind: NotifyTargetKind) -> None:
    hass = make_hass(entities=("notify.anna", "light.kitchen"), services=("mobile", "send_message"))
    assert classify(hass, target) is kind


def test_entity_wins_over_service_with_same_name() -> None:
    hass = make_hass(entities=("notify.both",), services=("both",))
    assert classify(hass, "notify.both") is NotifyTargetKind.NOTIFY_ENTITY


def test_check_rejects_unknown_target_and_accepts_known() -> None:
    notifier = HassNotifier(make_hass(entities=("notify.anna",)))
    notifier.check("notify.anna")
    with pytest.raises(InvalidNotifyTargetError):
        notifier.check("notify.gone")


async def test_send_to_entity_uses_send_message() -> None:
    hass = make_hass(entities=("notify.anna",))
    await HassNotifier(hass).async_send("notify.anna", "T", "M")
    hass.services.async_call.assert_awaited_once_with(
        "notify",
        "send_message",
        {"entity_id": "notify.anna", "title": "T", "message": "M"},
        blocking=True,
    )


async def test_send_to_legacy_service() -> None:
    hass = make_hass(services=("mobile",))
    await HassNotifier(hass).async_send("notify.mobile", "T", "M")
    hass.services.async_call.assert_awaited_once_with(
        "notify", "mobile", {"title": "T", "message": "M"}, blocking=True
    )


async def test_send_checks_target_again() -> None:
    hass = make_hass()
    with pytest.raises(InvalidNotifyTargetError):
        await HassNotifier(hass).async_send("notify.gone", "T", "M")
    hass.services.async_call.assert_not_awaited()


async def test_service_failure_becomes_notify_failed() -> None:
    hass = make_hass(entities=("notify.anna",))
    hass.services.async_call.side_effect = HomeAssistantError("boom")
    with pytest.raises(NotifyFailedError):
        await HassNotifier(hass).async_send("notify.anna", "T", "M")


async def test_timeout_becomes_notify_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "custom_components.task_wheel.infrastructure.notifier.hass_notifier.NOTIFY_TIMEOUT_SECONDS",
        0.01,
    )
    hass = make_hass(entities=("notify.anna",))

    async def slow(*_args: object, **_kwargs: object) -> None:
        await asyncio.sleep(1)

    hass.services.async_call.side_effect = slow
    with pytest.raises(NotifyFailedError):
        await HassNotifier(hass).async_send("notify.anna", "T", "M")


def test_factory_covers_every_kind() -> None:
    hass = make_hass()
    senders = {kind: NotifierFactory.create(kind, hass) for kind in NotifyTargetKind}
    assert isinstance(senders[NotifyTargetKind.NOTIFY_ENTITY], EntitySender)
    assert isinstance(senders[NotifyTargetKind.NOTIFY_SERVICE], ServiceSender)
    assert isinstance(senders[NotifyTargetKind.NONE], NoSender)


def test_text_files_have_identical_structure() -> None:
    files = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in TEXTS.glob("*.json")}
    assert {"de", "en"} <= files.keys()
    shape = {lang: {k: sorted(v) for k, v in data.items()} for lang, data in files.items()}
    assert shape["de"] == shape["en"]


def test_catalog_falls_back_to_english_for_unknown_or_unsafe_language() -> None:
    english = load_catalog(TEXTS, "en").render("swapped", "title")
    assert load_catalog(TEXTS, "xx").render("swapped", "title") == english
    assert load_catalog(TEXTS, "../en").render("swapped", "title") == english
    assert load_catalog(TEXTS, "de").render("swapped", "title") != english


def test_catalog_does_not_interpret_values_as_templates() -> None:
    text = load_catalog(TEXTS, "en").render("reminder", "title", schedule="{evil}")
    assert text == "Reminder: {evil}"
