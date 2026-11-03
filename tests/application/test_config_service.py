"""Kurznamen aus Namen ableiten."""

import pytest

from custom_components.task_wheel.application.config_service import slugify, unique_slug
from custom_components.task_wheel.const.limits import SLUG_MAX_LENGTH, SLUG_PATTERN


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
