"""Auswertung der Aggregate: KPIs, Punkte gegen fairen Anteil, Matrix, Hervorhebungen."""

import datetime as dt
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Final

from ...const.limits import RELIABILITY_MIN_CLOSED
from ..enums import AssignmentStatus, Period
from ..models import Round, Settings
from ..rules.periods import period_start
from ..status import PENDING_STATUSES, points_factor
from ..types import PersonId, TaskId
from .aggregate import StatRow
from .goals import ScheduleGoal

_S = AssignmentStatus
_DONE: Final = (_S.ON_TIME, _S.LATE)
# „Bleibt unerledigt“ zählt in der Statistik wie verpasst: die Aufgabe wurde nicht gemacht.
_UNDONE: Final = (_S.MISSED, _S.SKIPPED)
_CLOSED: Final = (*_DONE, *_UNDONE)
_PERFECT_INDEX: Final = 1.0
_HALF: Final = 0.5
_MIN_COMPARED: Final = 2


@dataclass(slots=True)
class Tally:
    """Summe der Anzahlen und Aufgabenpunkte je Status."""

    counts: dict[AssignmentStatus, int] = field(default_factory=dict)
    points: dict[AssignmentStatus, int] = field(default_factory=dict)

    def add(self, status: AssignmentStatus, count: int, points: int = 0) -> None:
        """Addiert Anzahl und Aufgabenpunkte zum Status."""
        self.counts[status] = self.counts.get(status, 0) + count
        self.points[status] = self.points.get(status, 0) + points

    def count(self, statuses: Iterable[AssignmentStatus]) -> int:
        """Anzahl der Zuteilungen in den Status."""
        return sum(self.counts.get(status, 0) for status in statuses)

    def awarded(self, settings: Settings) -> int:
        """Gutgeschriebene Punkte (Faktor je Status aus den Einstellungen)."""
        return sum(
            round(points * points_factor(status, settings))
            for status, points in self.points.items()
        )


def completion_rate(done: int, missed: int) -> float | None:
    """Erledigungsquote = erledigt / (erledigt + verpasst); ohne abgeschlossene Zuteilungen leer."""
    closed = done + missed
    return None if closed == 0 else done / closed


@dataclass(slots=True, frozen=True)
class Kpis:
    """Kennzahlen des Zeitraums."""

    assigned: int
    on_time: int
    late: int
    missed: int
    pending: int
    completion_rate: float | None


@dataclass(slots=True, frozen=True)
class Standing:
    """Punkte einer Person gegen ihren fairen Anteil (nach Belastbarkeit und Anwesenheit)."""

    person_id: PersonId
    points: int
    fair_points: float

    @property
    def difference(self) -> float:
        """Punkte minus fairer Anteil; positiv = mehr geleistet als fair."""
        return self.points - self.fair_points


@dataclass(slots=True, frozen=True)
class Reliable:
    """Zuverlässigste Person: Anteil pünktlich erledigter unter den abgeschlossenen Zuteilungen."""

    person_id: PersonId
    on_time_rate: float
    closed: int


@dataclass(slots=True, frozen=True)
class Highlights:
    """Glückspilz (am weitesten unter dem fairen Anteil), Pechvogel (darüber), Zuverlässigste."""

    lucky: PersonId | None
    unlucky: PersonId | None
    reliable: Reliable | None


@dataclass(slots=True, frozen=True)
class WeekRate:
    """Erledigungsquote der Runden, die in der Woche ab `week_start` begonnen haben."""

    week_start: dt.date
    done: int
    missed: int

    @property
    def rate(self) -> float | None:
        """Erledigungsquote der Woche (leer, wenn nichts abgeschlossen ist)."""
        return completion_rate(self.done, self.missed)


@dataclass(slots=True, frozen=True)
class StatisticsReport:
    """Auswertung für einen Zeitraum aus ganzen Kalendermonaten."""

    months: tuple[str, ...]
    kpis: Kpis
    standings: tuple[Standing, ...]
    fairness_index: float
    matrix: Mapping[TaskId, Mapping[PersonId, int]]
    weeks: tuple[WeekRate, ...]
    highlights: Highlights
    goals: tuple[ScheduleGoal, ...] = ()


def _kpis(tally: Tally) -> Kpis:
    done = tally.count(_DONE)
    missed = tally.count(_UNDONE)
    return Kpis(
        assigned=tally.count(tuple(_S)),
        on_time=tally.count((_S.ON_TIME,)),
        late=tally.count((_S.LATE,)),
        missed=missed,
        pending=tally.count(PENDING_STATUSES),
        completion_rate=completion_rate(done, missed),
    )


def _accumulate(
    rows: Iterable[StatRow],
) -> tuple[Tally, dict[PersonId, Tally], dict[TaskId, dict[PersonId, int]]]:
    """Summiert in einem Durchlauf: gesamt, je Person und Matrix Aufgabe mal Person."""
    total = Tally()
    per_person: dict[PersonId, Tally] = {}
    matrix: dict[TaskId, dict[PersonId, int]] = {}
    for row in rows:
        total.add(row.status, row.count, row.points)
        per_person.setdefault(row.person_id, Tally()).add(row.status, row.count, row.points)
        cells = matrix.setdefault(row.task_id, {})
        cells[row.person_id] = cells.get(row.person_id, 0) + row.count
    return total, per_person, matrix


def _standings(
    per_person: Mapping[PersonId, Tally], capacities: Mapping[PersonId, float], settings: Settings
) -> tuple[Standing, ...]:
    """Fairer Anteil = Gesamtpunkte der Personen mal Kapazität durch Summe der Kapazitäten."""
    points = {
        person_id: per_person[person_id].awarded(settings) if person_id in per_person else 0
        for person_id in capacities
    }
    total_points = sum(points.values())
    total_capacity = sum(capacities.values())
    return tuple(
        Standing(
            person_id,
            points[person_id],
            total_points * capacity / total_capacity if total_capacity > 0 else 0.0,
        )
        for person_id, capacity in sorted(capacities.items())
    )


def _fairness_index(standings: Iterable[Standing]) -> float:
    """1,0 = alle genau nach fairem Anteil; je größer die Abweichung der Anteile, desto kleiner."""
    entries = tuple(standings)
    total = sum(entry.points for entry in entries)
    if total <= 0:
        return _PERFECT_INDEX
    deviation = sum(abs(entry.points - entry.fair_points) for entry in entries) / total
    return min(max(_PERFECT_INDEX - _HALF * deviation, 0.0), _PERFECT_INDEX)


def _extreme(standings: tuple[Standing, ...], sign: int) -> PersonId | None:
    """Person mit der größten (`+1`) oder kleinsten (`-1`) Abweichung, nur bei echter Abweichung."""
    if len(standings) < _MIN_COMPARED:
        return None
    best = max(standings, key=lambda entry: sign * entry.difference)
    return best.person_id if sign * best.difference > 0 else None


def _reliable(per_person: Mapping[PersonId, Tally]) -> Reliable | None:
    candidates = []
    for person_id, tally in sorted(per_person.items()):
        closed = tally.count(_CLOSED)
        if closed >= RELIABILITY_MIN_CLOSED:
            candidates.append(Reliable(person_id, tally.count((_S.ON_TIME,)) / closed, closed))
    return max(candidates, key=lambda entry: (entry.on_time_rate, entry.closed), default=None)


def weekly_rates(rounds: Iterable[Round], week_starts: tuple[dt.date, ...]) -> tuple[WeekRate, ...]:
    """Erledigt/verpasst je Woche (Wochenbeginn Montag) aus den Rohdaten der Runden."""
    wanted = {start: Tally() for start in week_starts}
    for round_ in rounds:
        tally = wanted.get(period_start(Period.WEEK, round_.started_at))
        if tally is None:
            continue
        for assignment in round_.assignments:
            tally.add(assignment.status, 1)
    return tuple(
        WeekRate(start, tally.count(_DONE), tally.count(_UNDONE)) for start, tally in wanted.items()
    )


def build_report(
    months: tuple[str, ...],
    rows: Iterable[StatRow],
    capacities: Mapping[PersonId, float],
    settings: Settings,
    weeks: tuple[WeekRate, ...],
) -> StatisticsReport:
    """Stellt die Auswertung aus den Zellen der Aggregate zusammen."""
    total, per_person, matrix = _accumulate(rows)
    standings = _standings(per_person, capacities, settings)
    highlights = Highlights(_extreme(standings, -1), _extreme(standings, 1), _reliable(per_person))
    return StatisticsReport(
        months, _kpis(total), standings, _fairness_index(standings), matrix, weeks, highlights
    )
