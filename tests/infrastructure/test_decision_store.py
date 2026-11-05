"""Entscheidungslog-Speicher: Laden, Speichern, Sortierung, Bereinigung, Migration."""

import datetime as dt

import pytest

from custom_components.task_wheel.application.decision_service import DecisionService
from custom_components.task_wheel.domain.decisions import DecisionFilter
from custom_components.task_wheel.domain.errors import StorageCorruptError, StorageVersionError
from custom_components.task_wheel.infrastructure.repository.config_store import ConfigStore
from custom_components.task_wheel.infrastructure.repository.decision_store import DecisionStore
from custom_components.task_wheel.infrastructure.repository.memory import MemoryStore
from custom_components.task_wheel.infrastructure.repository.migration import (
    CURRENT_VERSION,
    DECISION_MIGRATIONS,
    migrate,
)

from ..domain import factories as f

DAY = dt.timedelta(days=1)


async def test_decision_store_roundtrip_and_delayed_save():
    config = ConfigStore(MemoryStore())
    memory = MemoryStore()
    repo = DecisionStore(memory)
    await repo.async_load()
    service = DecisionService(config, repo, id_factory=iter(["d1", "d2"]).__next__)
    config.put_schedule(f.schedule())
    for when in (f.NOW, f.NOW - DAY):
        service.record_swap(
            f.assignment(swap=f.swap(), person_id="p2"), f.assignment(id="a9"), when
        )
    assert memory.pending is not None
    memory.flush_pending()
    reloaded = DecisionStore(MemoryStore(memory.data))
    await reloaded.async_load()
    assert list(reloaded.records) == ["d2", "d1"]  # nach Zeit geordnet, nicht nach Einfügung
    assert [r.id for r in reloaded.query(DecisionFilter())] == ["d1", "d2"]
    assert reloaded.purge(f.NOW) == 1 and reloaded.purge(f.NOW - 10 * DAY) == 0
    await reloaded.async_flush()


async def test_decision_store_rejects_corrupt_data():
    with pytest.raises(StorageCorruptError):
        await DecisionStore(MemoryStore({"decisions": "x"})).async_load()
    with pytest.raises(StorageCorruptError):
        await DecisionStore(MemoryStore([])).async_load()


def test_decision_migrations_only_step_to_the_current_version():
    assert migrate("task_wheel.decisions", {"decisions": []}, CURRENT_VERSION, DECISION_MIGRATIONS)
    with pytest.raises(StorageVersionError):
        migrate("task_wheel.decisions", {}, (1, 1), DECISION_MIGRATIONS)
