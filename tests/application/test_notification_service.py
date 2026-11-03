"""NotificationService: Empfänger, Texte, Fehlerisolation, Zielprüfung."""

import asyncio
from pathlib import Path

import pytest

from custom_components.task_wheel.application.notification_service import NotificationService
from custom_components.task_wheel.const import notification as c
from custom_components.task_wheel.domain.errors import (
    InvalidNotifyTargetError,
    NotifyFailedError,
)
from custom_components.task_wheel.domain.models import Round
from custom_components.task_wheel.infrastructure.notifier.texts import load_catalog

from ..domain import factories as f
from .world import World

TEXTS = Path(__file__).parents[2] / "custom_components" / "task_wheel" / c.TEXTS_DIRECTORY


class FakeNotifier:
    """Merkt sich Sendungen; Ziele in `broken` scheitern, Ziele in `unknown` gibt es nicht."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []
        self.broken: set[str] = set()
        self.unknown: set[str] = set()

    def check(self, target: str) -> None:
        if target in self.unknown:
            raise InvalidNotifyTargetError(target)

    async def async_send(self, target: str, title: str, message: str) -> None:
        if target in self.broken:
            raise NotifyFailedError(target)
        self.sent.append((target, title, message))


class Setup:
    """Welt mit zwei Personen (p1 → notify.p1, p2 → notify.p2) und einem Service."""

    def __init__(self, language: str = "de") -> None:
        self.world = World()
        self.notifier = FakeNotifier()
        self.pending: list[object] = []
        self.world.config.put_person(
            f.person(id="p1", slug="p1", name="Anna", notify_target="notify.p1")
        )
        self.world.config.put_person(
            f.person(id="p2", slug="p2", name="Ben", notify_target="notify.p2")
        )
        self.service = NotificationService(
            self.world.config, self.notifier, load_catalog(TEXTS, language), self.pending.append
        )

    async def flush(self) -> None:
        await asyncio.gather(*self.pending)  # type: ignore[arg-type]
        self.pending.clear()

    def round_(self) -> Round:
        return f.finished_round(
            schedule_id="s1",
            assignments=(
                f.assignment(id="a1", task_id="t1", person_id="p1"),
                f.assignment(id="a2", task_id="t2", person_id="p2"),
                f.assignment(id="a3", task_id="t2", person_id="p1"),
            ),
        )


async def test_round_goes_to_every_target_with_summary_per_person() -> None:
    setup = Setup()
    setup.service.round_drawn(setup.round_())
    await setup.flush()
    assert [target for target, _, _ in setup.notifier.sent] == ["notify.p1", "notify.p2"]
    _, title, body = setup.notifier.sent[0]
    assert title == "Neue Aufgaben: Wochenrunde"
    assert body == "Anna: A (bis 10.11.), B (bis 10.11.)\nBen: B (bis 10.11.)"


async def test_english_texts() -> None:
    setup = Setup("en")
    setup.service.round_drawn(setup.round_())
    await setup.flush()
    assert setup.notifier.sent[0][1] == "New tasks: Wochenrunde"
    assert "A (due 11/10)" in setup.notifier.sent[0][2]


async def test_shared_target_is_notified_once_and_missing_target_skipped() -> None:
    setup = Setup()
    setup.world.config.put_person(
        f.person(id="p2", slug="p2", name="Ben", notify_target="notify.p1")
    )
    setup.world.config.put_person(f.person(id="p3", slug="p3", name="Cem", notify_target=None))
    setup.service.round_drawn(setup.round_())
    await setup.flush()
    assert [target for target, _, _ in setup.notifier.sent] == ["notify.p1"]


async def test_schedule_without_notify_stays_silent() -> None:
    setup = Setup()
    setup.world.config.put_schedule(f.schedule(notify=False))
    setup.service.round_drawn(setup.round_())
    await setup.flush()
    assert setup.notifier.sent == []


@pytest.mark.parametrize("schedule_id", ["unknown"])
async def test_round_of_unknown_schedule_or_without_assignments_stays_silent(
    schedule_id: str,
) -> None:
    setup = Setup()
    setup.service.round_drawn(f.finished_round(schedule_id=schedule_id))
    setup.service.round_drawn(f.finished_round(assignments=()))
    await setup.flush()
    assert setup.notifier.sent == []
    assert setup.pending == []


async def test_swap_goes_to_new_owner_only() -> None:
    setup = Setup()
    swapped = f.assignment(person_id="p2", swap=f.swap(), task_id="t1")
    setup.service.assignment_swapped(swapped)
    await setup.flush()
    assert [(t, title) for t, title, _ in setup.notifier.sent] == [
        ("notify.p2", "Aufgabe übernommen")
    ]
    assert setup.notifier.sent[0][2] == "Anna hat dir „A“ übergeben (bis 10.11.)."


async def test_reminder_goes_to_everyone_regardless_of_notify_flag() -> None:
    setup = Setup()
    schedule = f.schedule(notify=False)
    setup.service.reminder_due(schedule, 14)
    await setup.flush()
    assert len(setup.notifier.sent) == 2
    assert setup.notifier.sent[0][1:] == (
        "Erinnerung: Wochenrunde",
        "„Wochenrunde“ wurde seit 14 Tagen nicht ausgelost.",
    )


async def test_failing_target_does_not_block_others(caplog: pytest.LogCaptureFixture) -> None:
    setup = Setup()
    setup.notifier.broken.add("notify.p1")
    setup.service.round_drawn(setup.round_())
    await setup.flush()
    assert [target for target, _, _ in setup.notifier.sent] == ["notify.p2"]
    assert "notify.p1" in caplog.text


async def test_long_message_is_truncated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(c, "NOTIFY_MESSAGE_MAX_LENGTH", 20)
    setup = Setup()
    setup.service.round_drawn(setup.round_())
    await setup.flush()
    body = setup.notifier.sent[0][2]
    assert len(body) == 20
    assert body.endswith(c.NOTIFY_ELLIPSIS)


def test_check_target() -> None:
    setup = Setup()
    setup.notifier.unknown.add("notify.gone")
    setup.service.check_target(None)
    setup.service.check_target("notify.p1")
    with pytest.raises(InvalidNotifyTargetError):
        setup.service.check_target("notify.gone")


def test_unnamed_swap_giver_and_deleted_task_use_ids() -> None:
    setup = Setup()
    setup.service.assignment_swapped(f.assignment(task_id="gone", person_id="p2", swap=None))
    assert len(setup.pending) == 1
    setup.pending[0].close()  # type: ignore[attr-defined]
