"""Gemeinsame Test-Einstellungen."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Erlaubt das Laden der Integration aus custom_components."""
