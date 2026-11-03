"""Konfigurations- und Verlaufsspeicher: Laden, Speichern, Indizes, Grenzen, Migration."""

import datetime as dt
from typing import TYPE_CHECKING

import pytest

from custom_components.task_wheel.const import defaults, limits
from custom_components.task_wheel.const.keys import KEY_AGGREGATES, KEY_ROUNDS, STORE_CONFIG
from custom_components.task_wheel.domain.enums import AssignmentStatus
from custom_components.task_wheel.domain.errors import (
    LimitReachedError,
    NotFoundError,
    StorageCorruptError,
    StorageVersionError,
)
from custom_components.task_wheel.infrastructure.repository.config_store import ConfigStore
from custom_components.task_wheel.infrastructure.repository.history_store import HistoryStore
from custom_components.task_wheel.infrastructure.repository.memory import MemoryStore
from custom_components.task_wheel.infrastructure.repository.migration import migrate

from ..domain import factories as f

if TYPE_CHECKING:
    from custom_components.task_wheel.application.protocols import (
        ConfigRepository,
        HistoryRepository,
    )

DAY = dt.timedelta(days=1)


async def _reload_config(store: MemoryStore) -> ConfigStore:
    repo = ConfigStore(MemoryStore(store.data))
    await repo.async_load()
    return repo


async def test_config_roundtrip_and_delayed_save() -> None:
    memory = MemoryStore()
    repo: ConfigRepository = ConfigStore(memory)
    await repo.async_load()
    assert repo.persons == {}
    repo.put_person(f.person())
    repo.put_task(f.task())
    repo.put_schedule(f.schedule())
    repo.set_settings(f.settings(jokers_per_month=5))
    assert memory.data is None
    assert memory.delay == defaults.STORE_SAVE_DELAY_SECONDS
    memory.flush_pending()
    loaded = await _reload_config(memory)
    assert loaded.persons == {"p1": f.person()}
    assert loaded.tasks == {"t1": f.task()}
    assert loaded.schedules == {"s1": f.schedule()}
    assert loaded.settings.jokers_per_month == 5


async def test_config_flush_saves_immediately() -> None:
    memory = MemoryStore()
    repo = ConfigStore(memory)
    repo.put_person(f.person())
    await repo.async_flush()
    assert memory.pending is None
    assert (await _reload_config(memory)).persons == {"p1": f.person()}


async def test_config_replace_remove_and_not_found() -> None:
    repo = ConfigStore(MemoryStore())
    repo.put_person(f.person())
    repo.put_person(f.person(name="Anna B."))
    assert repo.persons["p1"].name == "Anna B."
    repo.remove_person("p1")
    repo.put_task(f.task())
    repo.remove_task("t1")
    repo.put_schedule(f.schedule())
    repo.remove_schedule("s1")
    assert not repo.persons
    assert not repo.tasks
    assert not repo.schedules
    with pytest.raises(NotFoundError):
        repo.remove_person("p1")


def test_config_views_are_read_only() -> None:
    repo = ConfigStore(MemoryStore())
    with pytest.raises(TypeError):
        repo.persons["x"] = f.person()  # type: ignore[index]


def test_config_limit() -> None:
    repo = ConfigStore(MemoryStore())
    for index in range(limits.MAX_PERSONS):
        repo.put_person(f.person(id=f"p{index}"))
    with pytest.raises(LimitReachedError):
        repo.put_person(f.person(id="extra"))
    repo.put_person(f.person(id="p0", name="Ersetzt"))


@pytest.mark.parametrize(
    "raw",
    [
        [],
        {"persons": [], "tasks": [], "schedules": []},
        {"persons": [{"id": "x"}], "tasks": [], "schedules": [], "settings": {}},
        {"persons": [], "tasks": [], "schedules": [], "settings": {"jokers_per_month": 99}},
    ],
)
async def test_config_corrupt_data_is_rejected(raw: object) -> None:
    repo = ConfigStore(MemoryStore(raw))
    with pytest.raises(StorageCorruptError):
        await repo.async_load()
    assert not repo.persons


def _history() -> tuple[HistoryStore, MemoryStore]:
    memory = MemoryStore()
    return HistoryStore(memory), memory


def _round(round_id: str, start: dt.datetime, *assignments: object) -> object:
    return f.finished_round(
        id=round_id,
        started_at=start,
        finished_at=start,
        assignments=tuple(assignments),
    )


def test_history_indexes_follow_changes() -> None:
    repo: HistoryRepository = HistoryStore(MemoryStore())
    open_a = f.assignment(id="a1", round_id="r1", person_id="p1", task_id="t1")
    done_b = f.assignment(
        id="a2",
        round_id="r1",
        person_id="p1",
        task_id="t2",
        status=AssignmentStatus.ON_TIME,
        done_at=f.NOW,
    )
    repo.put_round(_round("r1", f.NOW, open_a, done_b))  # type: ignore[arg-type]
    assert [a.id for a in repo.open_assignments("p1")] == ["a1"]
    assert repo.get_assignment("a2") == done_b
    assert repo.get_assignment("nope") is None
    assert repo.open_assignments("nobody") == ()
    assert repo.last_assignment("zzz") is None

    finished = f.assignment(
        id="a1",
        round_id="r1",
        person_id="p1",
        task_id="t1",
        status=AssignmentStatus.LATE,
        done_at=f.NOW,
    )
    repo.put_round(_round("r1", f.NOW, finished, done_b))  # type: ignore[arg-type]
    assert repo.open_assignments("p1") == ()
    assert repo.get_assignment("a1") == finished


def test_history_last_assignment_and_ordering() -> None:
    repo = HistoryStore(MemoryStore())
    newer = f.assignment(id="a2", round_id="r2", task_id="t1")
    older = f.assignment(id="a1", round_id="r1", task_id="t1")
    repo.put_round(_round("r2", f.NOW, newer))  # type: ignore[arg-type]
    repo.put_round(_round("r1", f.NOW - 3 * DAY, older))  # type: ignore[arg-type]
    assert list(repo.rounds) == ["r1", "r2"]
    assert repo.last_assignment("t1") == newer
    assert [a.id for a in repo.assignments_since(f.NOW - DAY)] == ["a2"]
    assert [a.id for a in repo.assignments_since(f.NOW - 5 * DAY)] == ["a2", "a1"]


async def test_history_roundtrip_aggregates_and_purge() -> None:
    repo, memory = _history()
    old = f.assignment(id="a1", round_id="r1", task_id="t1")
    new = f.assignment(id="a2", round_id="r2", task_id="t1")
    repo.put_round(_round("r1", f.NOW - 400 * DAY, old))  # type: ignore[arg-type]
    repo.put_round(_round("r2", f.NOW, new))  # type: ignore[arg-type]
    repo.set_aggregates({"2026-11": {"p1": 3}})
    memory.flush_pending()

    loaded = HistoryStore(MemoryStore(memory.data))
    await loaded.async_load()
    assert list(loaded.rounds) == ["r1", "r2"]
    assert loaded.aggregates == {"2026-11": {"p1": 3}}
    assert loaded.last_assignment("t1") == new

    assert await loaded.async_purge(f.NOW - 365 * DAY) == 1
    assert list(loaded.rounds) == ["r2"]
    assert loaded.get_assignment("a1") is None
    assert await loaded.async_purge(f.NOW - 365 * DAY) == 0
    await loaded.async_flush()


async def test_history_empty_load_and_corrupt() -> None:
    repo, _ = _history()
    await repo.async_load()
    assert not repo.rounds
    raws: tuple[object, ...] = ([], {KEY_ROUNDS: []}, {KEY_ROUNDS: [{"id": 1}], KEY_AGGREGATES: {}})
    for raw in raws:
        with pytest.raises(StorageCorruptError):
            await HistoryStore(MemoryStore(raw)).async_load()


def test_history_round_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(limits, "MAX_STORED_ROUNDS", 1)
    repo = HistoryStore(MemoryStore())
    repo.put_round(_round("r1", f.NOW))  # type: ignore[arg-type]
    repo.put_round(_round("r1", f.NOW))  # type: ignore[arg-type]
    with pytest.raises(LimitReachedError):
        repo.put_round(_round("r2", f.NOW))  # type: ignore[arg-type]


async def test_history_too_many_rounds_on_load(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(limits, "MAX_STORED_ROUNDS", 0)
    raw = {KEY_ROUNDS: [f.finished_round().to_dict()], KEY_AGGREGATES: {}}
    with pytest.raises(StorageCorruptError):
        await HistoryStore(MemoryStore(raw)).async_load()


def test_migration_chain_and_errors() -> None:
    steps = {
        (1, 0): ((1, 1), lambda d: {**d, "a": 1}),
        (1, 1): ((1, 2), lambda d: {**d, "b": 2}),
    }
    assert migrate(STORE_CONFIG, {}, (1, 0), steps, (1, 2)) == {"a": 1, "b": 2}
    assert migrate(STORE_CONFIG, {"x": 0}, (1, 2), steps, (1, 2)) == {"x": 0}
    with pytest.raises(StorageVersionError):
        migrate(STORE_CONFIG, {}, (0, 9), steps, (1, 2))
    with pytest.raises(StorageVersionError):
        migrate(STORE_CONFIG, {}, (2, 0), steps, (1, 2))


def test_history_replacing_round_with_new_start_keeps_order() -> None:
    repo = HistoryStore(MemoryStore())
    repo.put_round(_round("r1", f.NOW - DAY))  # type: ignore[arg-type]
    repo.put_round(_round("r2", f.NOW))  # type: ignore[arg-type]
    repo.put_round(_round("r1", f.NOW + DAY))  # type: ignore[arg-type]
    assert list(repo.rounds) == ["r2", "r1"]
