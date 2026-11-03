"""FanOutRoundEvents: alle Empfänger werden gerufen, ein Fehler bleibt isoliert."""

import logging

import pytest

from custom_components.task_wheel.application.fanout import FanOutRoundEvents
from custom_components.task_wheel.application.protocols import NoEvents

from ..domain import factories as f


class Recorder(NoEvents):
    """Merkt sich die Namen der Meldungen."""

    def __init__(self) -> None:
        self.seen: list[str] = []

    def round_drawn(self, round_) -> None:
        self.seen.append("drawn")

    def reminder_due(self, schedule, days_since) -> None:
        self.seen.append("reminder")

    def assignment_completed(self, assignment) -> None:
        self.seen.append("completed")

    def assignment_swapped(self, assignment) -> None:
        self.seen.append("swapped")

    def assignment_missed(self, assignment) -> None:
        self.seen.append("missed")

    def round_deleted(self, round_) -> None:
        self.seen.append("deleted")

    def animation_requested(self, round_, target) -> None:
        self.seen.append(f"animate:{target}")


class Broken(NoEvents):
    """Wirft bei jeder Meldung."""

    def round_drawn(self, round_) -> None:
        raise RuntimeError("kaputt")


def _all(events: FanOutRoundEvents) -> None:
    assignment = f.assignment()
    round_ = f.finished_round()
    events.round_drawn(round_)
    events.reminder_due(f.schedule(), 3)
    events.assignment_completed(assignment)
    events.assignment_swapped(assignment)
    events.assignment_missed(assignment)
    events.round_deleted(round_)
    events.animation_requested(round_, "media_player.tv")


def test_every_sink_receives_every_message() -> None:
    first, second = Recorder(), Recorder()
    _all(FanOutRoundEvents(first, second))
    expected = [
        "drawn",
        "reminder",
        "completed",
        "swapped",
        "missed",
        "deleted",
        "animate:media_player.tv",
    ]
    assert first.seen == expected
    assert second.seen == expected


def test_failing_sink_does_not_stop_the_others(caplog: pytest.LogCaptureFixture) -> None:
    after = Recorder()
    with caplog.at_level(logging.ERROR):
        _all(FanOutRoundEvents(Broken(), after))
    assert after.seen[0] == "drawn"
    assert "Meldung nicht verarbeitet" in caplog.text


def test_without_sinks_nothing_happens() -> None:
    _all(FanOutRoundEvents())
