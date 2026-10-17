"""AirJet intensity levels mirrored from the shipped V01 controls."""

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError

from .entity import BestwayEntity

LEVELS = {"off": 0, "low": 50, "high": 100}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([BestwayBubbles(entry.runtime_data)])


class BestwayBubbles(BestwayEntity, SelectEntity):
    _attr_name = "Bubbles"
    _attr_icon = "mdi:hot-tub"
    _attr_options = list(LEVELS)

    def __init__(self, coordinator):
        super().__init__(coordinator, "bubbles")

    @property
    def current_option(self):
        value = self.coordinator.data.bubbles
        if value == 0:
            return "off"
        if 1 <= value <= 99:
            return "low"
        if value == 100:
            return "high"
        return None

    async def async_select_option(self, option):
        if option not in LEVELS:
            raise HomeAssistantError("Unsupported bubble intensity")
        await self.coordinator.async_apply({"bubbles": LEVELS[option]})
