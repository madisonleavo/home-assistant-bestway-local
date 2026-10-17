"""HA fixtures. Hardware tests use independent simulated protocol endpoints."""

import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load the local custom integration."""
