"""Allowlisted diagnostics exclude endpoint, MAC, device ID and credentials."""

from .coordinator import BestwayConfigEntry


async def async_get_config_entry_diagnostics(hass, entry: BestwayConfigEntry):
    coordinator = entry.runtime_data
    data = coordinator.data
    identity = coordinator.client.identity
    return {
        "product_key": identity.product_key if identity else None,
        "wifi_firmware": identity.wifi_firmware if identity else None,
        "available": coordinator.last_update_success and not coordinator.closing,
        "poll_interval": coordinator.interval,
        "raw_status": data.raw.hex() if data else None,
        "control_policy": "single attempt; device readback; no replay",
    }
