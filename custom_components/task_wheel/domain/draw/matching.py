"""Zuordnung Personen ↔ Aufgaben: so viele Aufgaben verteilen wie möglich (Kuhn-Verfahren)."""

from collections.abc import Sequence

from ..types import PersonId


def max_matching(options: Sequence[frozenset[PersonId]]) -> int:
    """Größte Zahl an Aufgaben, die je eine eigene Person bekommen (`options[i]` = Kandidaten)."""
    owner: dict[PersonId, int] = {}

    def place(task: int, seen: set[PersonId]) -> bool:
        for person in options[task]:
            if person in seen:
                continue
            seen.add(person)
            if person not in owner or place(owner[person], seen):
                owner[person] = task
                return True
        return False

    return sum(place(task, set()) for task in range(len(options)))


def safe_winners(
    candidates: frozenset[PersonId], rest: Sequence[frozenset[PersonId]]
) -> frozenset[PersonId]:
    """Kandidaten, die den Rest nicht schlechter stellen als die bestmögliche Zuordnung.

    `rest` sind die Kandidaten der noch folgenden Aufgaben. Eine Person ist sicher, wenn die
    Aufgabe an sie zu vergeben und den Rest ohne sie zu verteilen genauso viele Aufgaben
    ergibt wie die beste Zuordnung aller zusammen.
    """
    best = max_matching([candidates, *rest])
    return frozenset(
        person for person in candidates if 1 + max_matching([o - {person} for o in rest]) == best
    )
