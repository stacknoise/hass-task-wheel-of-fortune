"""Ein- und Ausgabetypen der Ziehung (unveränderlich)."""

import datetime as dt
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from ..availability.calendar import PersonAvailability
from ..deadline import DeadlineWindow
from ..enums import ExclusionReason
from ..models import Person
from ..types import PersonId, TaskId


class RandomSource(Protocol):
    """Zufallsquelle: `secrets.SystemRandom` in Produktion, ein fester Zufall in Tests."""

    def random(self) -> float:
        """Liefert eine Zahl im Bereich [0, 1)."""
        ...


@dataclass(slots=True, frozen=True)
class DrawContext:
    """Zustand zum Zeitpunkt der Runde.

    `points` sind die Punkte je Person im Fairness-Fenster; `last_holders` nennt je Aufgabe die
    Person der letzten Zuteilung; `round_holders` sind die Personen, die in dieser Runde schon
    eine Aufgabe gezogen haben; `window` ist der Zeitraum, in dem die Aufgaben der Runde gelten.
    """

    now: dt.datetime
    persons: Mapping[PersonId, Person]
    availability: Mapping[PersonId, PersonAvailability]
    points: Mapping[PersonId, float]
    last_holders: Mapping[TaskId, PersonId]
    fairness_window_days: int
    window: DeadlineWindow
    round_holders: frozenset[PersonId] = frozenset()


@dataclass(slots=True, frozen=True)
class Exclusion:
    """Eine Person und der Grund, warum sie nicht im Rad ist."""

    person_id: PersonId
    reason: ExclusionReason


@dataclass(slots=True, frozen=True)
class TaskReplacement:
    """Eine Aufgabe, die der Admin vor dem Start gegen eine der Runde tauschen könnte."""

    task_id: TaskId
    doable: bool


@dataclass(slots=True, frozen=True)
class CandidateSelection:
    """Ergebnis der Filterkette: Kandidaten, Personen im Rad und Ausschlüsse.

    Gewinnen darf nur, wer Kandidat ist (der Rest der Runde bleibt vergebbar). Im Rad stehen
    alle, die die Aufgabe grundsätzlich bekommen könnten; so dreht es auch dann mit allen,
    wenn der Ausgang durch die Runde schon feststeht.
    """

    candidates: Sequence[Person]
    exclusions: Sequence[Exclusion]
    wheel: Sequence[Person] = ()


@dataclass(slots=True, frozen=True)
class WeightInput:
    """Zahlen, aus denen ein Gewicht entsteht: Kapazität im Fenster und bisherige Punkte."""

    person_id: PersonId
    capacity: float
    points: float


@dataclass(slots=True, frozen=True)
class Segment:
    """Segment im Rad: Gewicht und normierte Chance (Summe aller Chancen = 1)."""

    person_id: PersonId
    weight: float
    chance: float


@dataclass(slots=True, frozen=True)
class TaskDraw:
    """Ergebnis für eine Aufgabe; ohne Gewinner ist sie „nicht verteilbar“."""

    task_id: TaskId
    winner_id: PersonId | None
    chance: float
    segments: Sequence[Segment]
    exclusions: Sequence[Exclusion]

    @property
    def distributable(self) -> bool:
        """Wahr, wenn eine Person gezogen wurde."""
        return self.winner_id is not None
