"""Machbarkeit: wer kann eine Aufgabe im Zeitraum der Frist übernehmen (KONZEPT §5.2).

Eine Person ist Kandidat, wenn sie die Aufgabe laut Konfiguration bekommen darf, nicht pausiert
und belastbar genug ist und (sofern die Aufgabe Abwesenheit beachtet) irgendwann im Fenster
`DrawContext.window` anwesend ist. Die Besetzung der Runde bleibt außen vor. Dieselbe Prüfung
nutzen die Auslosung, der Entscheidungslog und der Austausch von Aufgaben.
"""

from collections.abc import Iterable, MutableMapping, Sequence

from ..models import Task
from ..types import PersonId, TaskId
from .candidates import CandidateSelector
from .matching import assignable_count, unplaceable
from .types import DrawContext

_SELECTOR = CandidateSelector()


def feasible_persons(task: Task, context: DrawContext) -> frozenset[PersonId]:
    """Personen, die `task` im Fenster des Kontexts übernehmen können."""
    return _SELECTOR.eligible(task, context)


def participants(tasks: Iterable[Task], context: DrawContext) -> frozenset[PersonId]:
    """Personen, die im Fenster mindestens eine der Aufgaben übernehmen können (Teilnehmer)."""
    return frozenset().union(*(feasible_persons(task, context) for task in tasks))


def is_feasible(task: Task, context: DrawContext) -> bool:
    """Ob mindestens eine Person `task` im Fenster übernehmen kann."""
    return bool(feasible_persons(task, context))


def feasible_tasks(tasks: Iterable[Task], context: DrawContext) -> tuple[Task, ...]:
    """Die Aufgaben, die im Fenster mindestens eine Person übernehmen kann (Reihenfolge bleibt)."""
    return tuple(task for task in tasks if is_feasible(task, context))


def assignable_tasks(tasks: Iterable[Task], context: DrawContext) -> int:
    """Wie viele der Aufgaben gleichzeitig vergeben werden können (je Person eine)."""
    return assignable_count([feasible_persons(task, context) for task in tasks])


def unassignable_tasks(
    tasks: Iterable[Task],
    context: DrawContext,
    memo: MutableMapping[TaskId, frozenset[PersonId]] | None = None,
) -> tuple[Task, ...]:
    """Aufgaben, die nicht alle zugleich vergeben werden können (je Person höchstens eine).

    Genannt werden alle Aufgaben, bei denen es leer ausgehen könnte: die ohne mögliche Person und
    die, die um zu wenige Personen konkurrieren. Leer, wenn die Runde vollständig vergebbar ist.
    `memo` (Aufgabe → mögliche Personen) kann der Aufrufer über eine Runde teilen.
    """
    items = tuple(tasks)
    cache = {} if memo is None else memo
    options = [cache.setdefault(t.id, feasible_persons(t, context)) for t in items]
    return tuple(items[index] for index in sorted(unplaceable(options)))


def pick_assignable(
    tasks: Sequence[Task], context: DrawContext, priority: Sequence[int]
) -> tuple[Task, ...]:
    """Die größte Auswahl, die sich vollständig vergeben lässt (je Person höchstens eine Aufgabe).

    `priority` sind die Indizes von `tasks`, wichtigste zuerst. Jede Aufgabe kommt dazu, wenn die
    Auswahl danach noch vollständig vergebbar bleibt (Greedy über die Zuordnung Personen ↔
    Aufgaben, die dafür eine Matroid-Struktur hat: das Ergebnis ist größtmöglich und bevorzugt
    die frühen Prioritäten). Aufgaben, die niemand übernehmen kann, kommen nie dazu. Die
    Reihenfolge der Auswahl bleibt die von `tasks`.
    """
    options = [feasible_persons(task, context) for task in tasks]
    chosen: list[int] = []
    for index in priority:
        trial = [*chosen, index]
        if assignable_count([options[i] for i in trial]) == len(trial):
            chosen = trial
    return tuple(tasks[i] for i in sorted(chosen))
