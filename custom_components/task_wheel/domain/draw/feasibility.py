"""Machbarkeit: wer kann eine Aufgabe im Zeitraum der Frist übernehmen (KONZEPT §5.2).

Eine Person ist Kandidat, wenn sie die Aufgabe laut Konfiguration bekommen darf, nicht pausiert
und belastbar genug ist und (sofern die Aufgabe Abwesenheit beachtet) irgendwann im Fenster
`DrawContext.window` anwesend ist. Die Besetzung der Runde bleibt außen vor. Dieselbe Prüfung
nutzen die Auslosung, der Entscheidungslog und der Austausch von Aufgaben.
"""

from collections.abc import Iterable

from ..models import Task
from ..types import PersonId
from .candidates import CandidateSelector
from .types import DrawContext

_SELECTOR = CandidateSelector()


def feasible_persons(task: Task, context: DrawContext) -> frozenset[PersonId]:
    """Personen, die `task` im Fenster des Kontexts übernehmen können."""
    return _SELECTOR.eligible(task, context)


def is_feasible(task: Task, context: DrawContext) -> bool:
    """Ob mindestens eine Person `task` im Fenster übernehmen kann."""
    return bool(feasible_persons(task, context))


def feasible_tasks(tasks: Iterable[Task], context: DrawContext) -> tuple[Task, ...]:
    """Die Aufgaben, die im Fenster mindestens eine Person übernehmen kann (Reihenfolge bleibt)."""
    return tuple(task for task in tasks if is_feasible(task, context))
