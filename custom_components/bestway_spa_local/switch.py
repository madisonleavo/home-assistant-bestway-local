"""Native explicit switches for V01 controls."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory

from .entity import BestwayEntity

SWITCHES = {
    "power": ("Power", "mdi:power"),
    "heat": ("Heater", "mdi:water-boiler"),
    "filter": ("Filter", "mdi:filter"),
    "locked": ("Panel lock", "mdi:lock"),
}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(BestwaySwitch(entry.runtime_data, key) for key in SWITCHES)


class BestwaySwitch(BestwayEntity, SwitchEntity):
    def __init__(self, coordinator, key):
        super().__init__(coordinator, key)
        self.key = key
        self._attr_name, self._attr_icon = SWITCHES[key]
        if key == "locked":
            self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self):
        state = self.coordinator.data
        if self.key == "heat":
            return bool(state.heat_code)
        if self.key == "filter":
            return bool(state.filter_code)
        return getattr(state, self.key)

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_apply({self.key: True})

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_apply({self.key: False})
