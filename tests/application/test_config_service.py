"""Kurznamen aus Namen ableiten."""

import datetime as dt
from dataclasses import replace

import pytest

from custom_components.task_wheel.application.config_service import slugify, unique_slug
from custom_components.task_wheel.const.limits import (
    MAX_ABSENCES_PER_PERSON,
    SLUG_MAX_LENGTH,
    SLUG_PATTERN,
)
from custom_components.task_wheel.domain.errors import NotFoundError, ValidationError
from custom_components.task_wheel.domain.models import OnceAbsence, WeeklyDaysAbsence

from ..websocket.harness import Api

TODAY = dt.date(2026, 11, 3)
DAY = dt.timedelta(days=1)


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("Anna", "anna"),
        ("Jörg Müller", "jorg_muller"),
        ("  --Küche & Bad!  ", "kuche_bad"),
        ("日本語", "item"),
        ("", "item"),
        (42, "item"),
    ],
)
def test_slugify(name: object, slug: str) -> None:
    assert slugify(name) == slug


def test_slugify_is_limited_and_valid() -> None:
    slug = slugify("a" * 200)
    assert len(slug) == SLUG_MAX_LENGTH
    assert SLUG_PATTERN.fullmatch(slug)


def test_unique_slug_counts_up_and_keeps_length() -> None:
    assert unique_slug("anna", ["ben"]) == "anna"
    assert unique_slug("anna", ["anna", "anna_2"]) == "anna_3"
    base = "a" * SLUG_MAX_LENGTH
    taken = unique_slug(base, [base])
    assert len(taken) == SLUG_MAX_LENGTH
    assert taken.endswith("_2")


def test_add_absence_drops_expired_one_time_absences_and_keeps_the_rest() -> None:
    api = Api()
    kept = WeeklyDaysAbsence(weekdays=frozenset({5, 6}))
    expired = OnceAbsence(start=TODAY - 9 * DAY, end=TODAY - DAY)
    running = OnceAbsence(start=TODAY - DAY, end=TODAY)
    api.config.put_person(replace(api.config.persons["p1"], absences=(expired, kept, running)))
    person = api.data.configuration.add_absence("p1", TODAY, TODAY + DAY, TODAY)
    assert person.absences == (kept, running, OnceAbsence(start=TODAY, end=TODAY + DAY))
    assert api.config.persons["p1"] == person


def test_add_absence_rejects_unknown_person_wrong_order_and_too_many() -> None:
    api = Api()
    with pytest.raises(NotFoundError):
        api.data.configuration.add_absence("nope", TODAY, TODAY, TODAY)
    with pytest.raises(ValidationError):
        api.data.configuration.add_absence("p1", TODAY, TODAY - DAY, TODAY)
    for number in range(MAX_ABSENCES_PER_PERSON):
        api.data.configuration.add_absence("p1", TODAY + number * DAY, TODAY + number * DAY, TODAY)
    with pytest.raises(ValidationError):
        api.data.configuration.add_absence("p1", TODAY, TODAY, TODAY)
