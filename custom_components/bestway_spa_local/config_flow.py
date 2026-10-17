"""UI configuration, identity-preserving reconfiguration and polling options."""

import asyncio

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlowWithReload
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback

from .const import CONF_PASSCODE, CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL, DOMAIN, normalize_mac
from .protocol import AuthenticationError, Client, ProtocolError, UnsupportedDeviceError


class BestwayFlow(ConfigFlow, domain=DOMAIN):
    """Create one entry for a confirmed local device."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BestwayOptionsFlow()

    async def async_step_user(self, user_input=None):
        return await self._configure("user", user_input)

    async def async_step_reconfigure(self, user_input=None):
        return await self._configure("reconfigure", user_input)

    async def _configure(self, step_id, user_input):
        errors = {}
        entry = self._get_reconfigure_entry() if step_id == "reconfigure" else None
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            # Hostname/IP only: prevent accidental URLs, whitespace or port strings.
            if not host or any(char in host for char in "/ :\t\n"):
                errors[CONF_HOST] = "invalid_host"
            else:
                client = Client(host, passcode=entry.data.get(CONF_PASSCODE) if entry else None)
                try:
                    async with asyncio.timeout(20):
                        await client.async_open()
                        await client.async_read_state()
                    identity = client.identity
                    mac = identity.mac
                    unique_id = normalize_mac(mac)
                    data = {
                        CONF_HOST: host,
                        "mac": mac,
                        "product_key": identity.product_key,
                        CONF_PASSCODE: client.passcode,
                    }
                    await self.async_set_unique_id(unique_id)
                    if entry:
                        self._abort_if_unique_id_mismatch()
                        return self.async_update_reload_and_abort(entry, data_updates=data)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=user_input.get(CONF_NAME) or "Bestway Spa",
                        data=data,
                    )
                except UnsupportedDeviceError:
                    errors["base"] = "unsupported_device"
                except AuthenticationError:
                    errors["base"] = "authentication_failed"
                except ProtocolError, OSError, TimeoutError:
                    errors["base"] = "cannot_connect"
                finally:
                    await client.async_close()
        fields = {vol.Required(CONF_HOST): str}
        if not entry:
            fields[vol.Optional(CONF_NAME)] = str
        schema = vol.Schema(fields)
        if entry:
            schema = self.add_suggested_values_to_schema(schema, entry.data)
        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors)


class BestwayOptionsFlow(OptionsFlowWithReload):
    """One bounded polling preference; HA handles the reload lifecycle."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLL_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                }
            ),
        )
