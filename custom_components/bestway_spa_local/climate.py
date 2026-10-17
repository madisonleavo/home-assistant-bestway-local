"""Native spa thermostat; off stops heating, not the circulation pump."""

import math

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError

from .entity import BestwayEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([BestwayClimate(entry.runtime_data)])


class BestwayClimate(BestwayEntity, ClimateEntity):
    _attr_name = None
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 1

    def __init__(self, coordinator):
        super().__init__(coordinator, "climate")

    @property
    def temperature_unit(self):
        return (
            UnitOfTemperature.CELSIUS
            if self.coordinator.data.unit == "C"
            else UnitOfTemperature.FAHRENHEIT
        )

    @property
    def current_temperature(self):
        return self.coordinator.data.current_temperature

    @property
    def target_temperature(self):
        return self.coordinator.data.target_temperature

    @property
    def min_temp(self):
        return 20 if self.coordinator.data.unit == "C" else 68

    @property
    def max_temp(self):
        return 40 if self.coordinator.data.unit == "C" else 104

    @property
    def hvac_mode(self):
        state = self.coordinator.data
        return HVACMode.HEAT if state.power and state.heat_code else HVACMode.OFF

    @property
    def hvac_action(self):
        state = self.coordinator.data
        if not state.power or state.heat_code == 0:
            return HVACAction.OFF
        if state.heat_code in (2, 4):
            return HVACAction.HEATING
        if state.heat_code in (1, 3):
            return HVACAction.IDLE
        return None

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            raise HomeAssistantError("An integer target temperature is required")
        if not self.min_temp <= temperature <= self.max_temp:
            raise HomeAssistantError("Target must be within the spa's native unit range")
        # HA converts service temperatures to the spa's native units first.
        values = {"target_temperature": math.floor(temperature + 0.5)}
        if (mode := kwargs.get("hvac_mode")) is not None:
            if mode not in self.hvac_modes:
                raise HomeAssistantError("Only off and heat modes are supported")
            if mode == HVACMode.HEAT and not self.coordinator.data.power:
                raise HomeAssistantError("Turn on spa power before enabling heating")
            values["heat"] = mode == HVACMode.HEAT
        await self.coordinator.async_apply(values)

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode not in self.hvac_modes:
            raise HomeAssistantError("Only off and heat modes are supported")
        # Heating from powered off requires an explicit power-on, matching the physical controls.
        if hvac_mode == HVACMode.HEAT and not self.coordinator.data.power:
            raise HomeAssistantError("Turn on spa power before enabling heating")
        await self.coordinator.async_apply({"heat": hvac_mode == HVACMode.HEAT})

    async def async_turn_on(self):
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        await self.async_set_hvac_mode(HVACMode.OFF)
