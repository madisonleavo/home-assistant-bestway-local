"""Observed temperatures and explicit operating states."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTemperature

from .entity import BestwayEntity

HEAT_STATES = {
    0: "off",
    1: "starting",
    2: "heating",
    3: "maintaining_idle",
    4: "maintaining_heating",
}
FILTER_STATES = {0: "off", 1: "starting", 2: "running", 3: "waiting"}
SENSORS = {
    "current_temperature": "Water temperature",
    "target_temperature": "Target temperature",
    "heater_state": "Heater state",
    "filter_state": "Filter state",
    "bubbles_level": "Bubbles level",
}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(BestwaySensor(entry.runtime_data, key) for key in SENSORS)


class BestwaySensor(BestwayEntity, SensorEntity):
    def __init__(self, coordinator, key):
        super().__init__(coordinator, key)
        self.key = key
        self._attr_name = SENSORS[key]
        if key.endswith("temperature"):
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key in ("heater_state", "filter_state"):
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = list(
                (HEAT_STATES if key == "heater_state" else FILTER_STATES).values()
            )
        else:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_native_unit_of_measurement = "%"

    @property
    def native_unit_of_measurement(self):
        if self.key.endswith("temperature"):
            return (
                UnitOfTemperature.CELSIUS
                if self.coordinator.data.unit == "C"
                else UnitOfTemperature.FAHRENHEIT
            )
        return "%" if self.key == "bubbles_level" else None

    @property
    def native_value(self):
        state = self.coordinator.data
        if self.key == "heater_state":
            return HEAT_STATES.get(state.heat_code)
        if self.key == "filter_state":
            return FILTER_STATES.get(state.filter_code)
        if self.key == "bubbles_level":
            return state.bubbles
        return getattr(state, self.key)

    @property
    def extra_state_attributes(self):
        if self.key == "heater_state":
            return {"raw_code": self.coordinator.data.heat_code}
        if self.key == "filter_state":
            return {"raw_code": self.coordinator.data.filter_code}
        return None
