"""Local Bestway spa integration; no cloud, broker or startup control writes."""

import contextlib

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, PLATFORMS
from .coordinator import BestwayConfigEntry, BestwayCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: BestwayConfigEntry) -> bool:
    """Set up a single verified spa; release resources on every failure path."""
    coordinator = BestwayCoordinator(hass, entry)
    entry.runtime_data = coordinator
    forwarding_started = False
    try:
        await coordinator.async_config_entry_first_refresh()
        forwarding_started = True
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        try:
            if forwarding_started:
                with contextlib.suppress(Exception):
                    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        finally:
            await coordinator.async_shutdown()
        raise

    async def stop(_event) -> None:
        await coordinator.async_shutdown()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BestwayConfigEntry) -> bool:
    """Remove entities, then stop owned networking; never operate the pump."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()
    return unloaded
