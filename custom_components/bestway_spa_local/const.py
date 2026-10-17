"""Stable integration identifiers and resource limits."""

from homeassistant.const import Platform

DOMAIN = "bestway_spa_local"
CONF_PASSCODE = "passcode"
CONF_POLL_INTERVAL = "poll_interval"
DEFAULT_POLL_INTERVAL = 15
PLATFORMS = [
    Platform.CLIMATE,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


def normalize_mac(value: str) -> str:
    """Match identity across discovery, config entries and entity IDs."""
    return value.lower().replace(":", "").replace("-", "")
