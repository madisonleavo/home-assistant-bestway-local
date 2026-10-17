"""Shared device identity and coordinator lifecycle for native entities."""

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, normalize_mac
from .coordinator import BestwayCoordinator


class BestwayEntity(CoordinatorEntity[BestwayCoordinator]):
    """Entity state comes from memory; I/O is confined to async operations."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BestwayCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        mac = entry.data["mac"]
        self._attr_unique_id = f"{normalize_mac(mac)}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, normalize_mac(mac))},
            connections={(CONNECTION_NETWORK_MAC, mac)},
            name=entry.title,
            manufacturer="Bestway",
            model=coordinator.client.profile.model,
            sw_version=coordinator.client.identity.wifi_firmware,
        )
