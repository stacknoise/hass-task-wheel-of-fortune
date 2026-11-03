"""Texte der Benachrichtigungen: Titel und Nachricht aus Meldung und Namen (reine Funktionen)."""

from collections.abc import Iterable
from dataclasses import dataclass

from ..const import notification as c
from ..domain.models import Assignment, Round, Schedule
from .names import person_name, task_name
from .protocols import ConfigRepository, Texts


@dataclass(slots=True, frozen=True)
class Message:
    """Fertiger Text einer Benachrichtigung."""

    title: str
    body: str


def _truncate(text: str) -> str:
    """Kürzt zu lange Texte (viele Zuteilungen) und kennzeichnet die Kürzung."""
    if len(text) <= c.NOTIFY_MESSAGE_MAX_LENGTH:
        return text
    return text[: c.NOTIFY_MESSAGE_MAX_LENGTH - len(c.NOTIFY_ELLIPSIS)] + c.NOTIFY_ELLIPSIS


def _due(texts: Texts, assignment: Assignment) -> str:
    """Frist im Datumsformat der Sprache."""
    return assignment.due_at.strftime(texts.render(c.TEXT_COMMON, c.TEXT_DATE_FORMAT))


def _task_item(config: ConfigRepository, texts: Texts, assignment: Assignment) -> str:
    """Aufgabe mit Frist."""
    return texts.render(
        c.TEXT_ROUND_DRAWN,
        c.TEXT_TASK_ITEM,
        task=task_name(config, assignment),
        due=_due(texts, assignment),
    )


def _by_person(assignments: Iterable[Assignment]) -> dict[str, list[Assignment]]:
    """Gruppiert nach Person; die Reihenfolge der ersten Zuteilung bleibt erhalten."""
    grouped: dict[str, list[Assignment]] = {}
    for item in assignments:
        grouped.setdefault(item.person_id, []).append(item)
    return grouped


def _person_lines(
    config: ConfigRepository, texts: Texts, assignments: Iterable[Assignment]
) -> list[str]:
    """Je Person eine Zeile mit ihren Aufgaben."""
    separator = texts.render(c.TEXT_COMMON, c.TEXT_LIST_SEPARATOR)
    return [
        texts.render(
            c.TEXT_ROUND_DRAWN,
            c.TEXT_PERSON_LINE,
            person=person_name(config, person_id),
            tasks=separator.join(_task_item(config, texts, item) for item in items),
        )
        for person_id, items in _by_person(assignments).items()
    ]


def drawn_message(
    config: ConfigRepository, texts: Texts, round_: Round, schedule: Schedule
) -> Message:
    """Ergebnis einer Runde: eine Zeile je Person."""
    lines = _person_lines(config, texts, round_.assignments)
    summary = texts.render(c.TEXT_COMMON, c.TEXT_LINE_SEPARATOR).join(lines)
    return Message(
        title=texts.render(c.TEXT_ROUND_DRAWN, c.TEXT_TITLE, schedule=schedule.name),
        body=_truncate(texts.render(c.TEXT_ROUND_DRAWN, c.TEXT_MESSAGE, summary=summary)),
    )


def swapped_message(config: ConfigRepository, texts: Texts, assignment: Assignment) -> Message:
    """Hinweis an die neue Person, dass sie eine Aufgabe übernommen hat."""
    giver = assignment.swap.from_person_id if assignment.swap is not None else ""
    return Message(
        title=texts.render(c.TEXT_SWAPPED, c.TEXT_TITLE),
        body=_truncate(
            texts.render(
                c.TEXT_SWAPPED,
                c.TEXT_MESSAGE,
                task=task_name(config, assignment),
                from_person=person_name(config, giver),
                due=_due(texts, assignment),
            )
        ),
    )


def reminder_message(texts: Texts, schedule: Schedule, days_since: int) -> Message:
    """Erinnerung, dass ein Zeitplan seit `days_since` Tagen nicht ausgelost wurde."""
    return Message(
        title=texts.render(c.TEXT_REMINDER, c.TEXT_TITLE, schedule=schedule.name),
        body=_truncate(
            texts.render(c.TEXT_REMINDER, c.TEXT_MESSAGE, schedule=schedule.name, days=days_since)
        ),
    )
