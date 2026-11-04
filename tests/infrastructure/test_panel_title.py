"""Tests für den sprachabhängigen Titel der Seitenleiste."""

import pytest

from custom_components.task_wheel.const.defaults import INTEGRATION_NAME, INTEGRATION_NAME_DE
from custom_components.task_wheel.infrastructure.panel import sidebar_title


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("de", INTEGRATION_NAME_DE),
        ("de-AT", INTEGRATION_NAME_DE),
        ("en", INTEGRATION_NAME),
        ("fr", INTEGRATION_NAME),
    ],
)
def test_sidebar_title(language: str, expected: str) -> None:
    assert sidebar_title(language) == expected
