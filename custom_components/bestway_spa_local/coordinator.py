"""Config-entry-owned networking, bounded polling and command readback."""

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_PASSCODE, CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL, DOMAIN, normalize_mac
from .protocol import Client, ProtocolError, SpaState

LOGGER = logging.getLogger(__name__)
type BestwayConfigEntry = ConfigEntry[BestwayCoordinator]


class BestwayCoordinator(DataUpdateCoordinator[SpaState]):
    """One client per entry; nothing in an entity property touches the network."""

    def __init__(self, hass: HomeAssistant, entry: BestwayConfigEntry) -> None:
        self.client = Client(entry.data[CONF_HOST], passcode=entry.data.get(CONF_PASSCODE))
        self.interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        self.failures = 0
        self.closing = False
        self._operations: set[asyncio.Task] = set()
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=self.interval),
            always_update=False,
        )

    def _check_identity(self) -> None:
        expected = self.config_entry.unique_id
        if self.client.identity is None or normalize_mac(self.client.identity.mac) != expected:
            raise ProtocolError("The configured address belongs to another device")

    def _save_passcode(self) -> None:
        if self.client.passcode and self.client.passcode != self.config_entry.data.get(
            CONF_PASSCODE
        ):
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, CONF_PASSCODE: self.client.passcode},
            )

    async def _async_update_data(self) -> SpaState:
        if self.closing:
            raise UpdateFailed("Integration is shutting down")
        task = asyncio.current_task()
        self._operations.add(task)
        try:
            await self.client.async_open()
            self._check_identity()
            state = await self.client.async_read_state()
            self._save_passcode()
        except (ProtocolError, OSError, TimeoutError) as err:
            if self.closing:
                raise UpdateFailed("Integration is shutting down") from err
            self.failures = min(self.failures + 1, 5)
            self.update_interval = timedelta(seconds=min(300, self.interval * 2**self.failures))
            if self.failures >= 3:
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"unreachable_{self.config_entry.entry_id}",
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="spa_unreachable",
                    translation_placeholders={"name": self.config_entry.title},
                )
            await self.client.async_close()
            raise UpdateFailed("Spa unavailable; retrying with bounded backoff") from err
        finally:
            self._operations.discard(task)
        self.failures = 0
        ir.async_delete_issue(self.hass, DOMAIN, f"unreachable_{self.config_entry.entry_id}")
        self.update_interval = timedelta(seconds=self.interval)
        return state

    async def async_apply(self, values: dict[str, bool | int]) -> None:
        """Report actual state after a single command; never silently queue writes."""
        if self.closing or not self.last_update_success:
            raise HomeAssistantError("Spa is unavailable")
        task = asyncio.current_task()
        self._operations.add(task)
        try:
            state = await self.client.async_set_values(values)
        except (ProtocolError, OSError, TimeoutError, ValueError) as err:
            await self.client.async_close()
            self.async_set_update_error(UpdateFailed("Command failed; refresh before trying again"))
            raise HomeAssistantError("Spa command was not confirmed; it was not retried") from err
        finally:
            self._operations.discard(task)
        if not self.closing:
            self.async_set_updated_data(state)

    async def async_shutdown(self) -> None:
        """Close the socket before cancelling pending operations; leave the spa alone."""
        if self.closing:
            return
        self.closing = True
        ir.async_delete_issue(self.hass, DOMAIN, f"unreachable_{self.config_entry.entry_id}")
        await super().async_shutdown()
        await self.client.async_close()
        pending = [task for task in self._operations if task is not asyncio.current_task()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        ir.async_delete_issue(self.hass, DOMAIN, f"unreachable_{self.config_entry.entry_id}")
