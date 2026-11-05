"""Zuordnung Personen ↔ Aufgaben: so viele Aufgaben verteilen wie möglich (Kuhn-Verfahren)."""

from collections import defaultdict, deque
from collections.abc import Sequence

from ..types import PersonId

type Options = Sequence[frozenset[PersonId]]
type Owners = dict[PersonId, int]


def _augment(options: Options, task: int, owner: Owners) -> bool:
    """Sucht für `task` eine Person, notfalls durch Umbesetzen (erweiternder Pfad)."""
    seen: set[PersonId] = set()

    def place(current: int) -> bool:
        for person in options[current]:
            if person in seen:
                continue
            seen.add(person)
            if person not in owner or place(owner[person]):
                owner[person] = current
                return True
        return False

    return place(task)


def _match(options: Options) -> Owners:
    """Eine größte Zuordnung als Person → Aufgabe."""
    owner: Owners = {}
    for task in range(len(options)):
        _augment(options, task, owner)
    return owner


def _free_persons(options: Options, owner: Owners, universe: frozenset[PersonId]) -> set[PersonId]:
    """Personen, die in irgendeiner größten Zuordnung ohne Aufgabe bleiben können."""
    tasks_of: dict[PersonId, list[int]] = defaultdict(list)
    for task, people in enumerate(options):
        for person in people:
            tasks_of[person].append(task)
    holder_of = {task: person for person, task in owner.items()}
    free = set(universe - owner.keys())
    queue = deque(free)
    while queue:
        person = queue.popleft()
        for task in tasks_of[person]:
            holder = holder_of.get(task)
            if holder is not None and holder not in free:
                free.add(holder)
                queue.append(holder)
    return free


def safe_winners(candidates: frozenset[PersonId], rest: Options) -> frozenset[PersonId]:
    """Kandidaten, die den Rest nicht schlechter stellen als die bestmögliche Zuordnung.

    `rest` sind die Kandidaten der noch folgenden Aufgaben. Eine Person ist sicher, wenn die
    Aufgabe an sie zu vergeben und den Rest ohne sie zu verteilen genauso viele Aufgaben
    ergibt wie die beste Zuordnung aller zusammen. Das gilt, wenn die Aufgabe selbst nichts
    zur besten Zuordnung beiträgt, oder wenn die Person im Rest frei bleiben kann.
    """
    owner = _match(rest)
    with_task = dict(owner)
    if not _augment([*rest, candidates], len(rest), with_task):
        return candidates
    universe = candidates.union(*rest)
    return candidates & _free_persons(rest, owner, universe)


def assignable_count(options: Options) -> int:
    """Wie viele Aufgaben gleichzeitig an verschiedene Personen gehen können (je Person eine)."""
    return len(_match(options))


def unplaceable(options: Options) -> frozenset[int]:
    """Aufgaben (Indizes), die in mindestens einer größten Zuordnung leer ausgehen.

    Reicht es nicht für alle Aufgaben, sind das die unvergebbaren samt jener, die um dieselben
    Personen konkurrieren (erreichbar über abwechselnd Aufgabe → Person → deren Aufgabe).
    Sind alle vergebbar, ist die Menge leer.
    """
    owner = _match(options)
    task_of = {task: person for person, task in owner.items()}
    queue = deque(index for index in range(len(options)) if index not in task_of)
    seen = set(queue)
    while queue:
        for person in options[queue.popleft()]:
            holder = owner[person]
            if holder not in seen:
                seen.add(holder)
                queue.append(holder)
    return frozenset(seen)
