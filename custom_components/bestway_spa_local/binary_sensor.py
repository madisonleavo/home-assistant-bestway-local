"""Target-reached is separate from the real fault indicators."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory

from .entity import BestwayEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [BestwayBinarySensor(entry.runtime_data, key) for key in ("target_reached", "fault")]
    )


class BestwayBinarySensor(BestwayEntity, BinarySensorEntity):
    def __init__(self, coordinator, key):
        super().__init__(coordinator, key)
        self.key = key
        self._attr_name = "Target reached" if key == "target_reached" else "Fault"
        if key == "fault":
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self):
        state = self.coordinator.data
        return state.target_reached if self.key == "target_reached" else bool(state.errors)

    @property
    def extra_state_attributes(self):
        if self.key == "fault":
            return {"codes": list(self.coordinator.data.errors)}
        return None
