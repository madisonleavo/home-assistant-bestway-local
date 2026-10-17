"""Exercise HA lifecycle using a simulated boundary, never a physical spa."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bestway_spa_local.protocol import decode_status

DOMAIN = "bestway_spa_local"
MAC = "aa:bb:cc:dd:ee:ff"


@pytest.fixture
def mock_client():
    state = decode_status(bytes.fromhex(Path("tests/fixtures/v01_status.hex").read_text()))
    client = SimpleNamespace(
        identity=SimpleNamespace(
            mac=MAC,
            product_key="d3ac9226d983470284b5d133cf4fd6b4",
            device_id="synthetic-device-id",
            wifi_firmware="test-fw",
        ),
        profile=SimpleNamespace(model="AirJet V01"),
        passcode="synthetic-private-passcode",
        last_state=state,
        async_open=AsyncMock(),
        async_read_state=AsyncMock(return_value=state),
        async_set_values=AsyncMock(return_value=state),
        async_close=AsyncMock(),
    )
    return client


@pytest.fixture
def entry(hass):
    result = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MAC.replace(":", ""),
        title="Milan",
        data={CONF_HOST: "192.0.2.10", "mac": MAC, "passcode": "synthetic-private-passcode"},
    )
    result.add_to_hass(hass)
    return result


async def test_flow_confirms_identity_and_closes_temporary_client(hass, mock_client):
    with (
        patch("custom_components.bestway_spa_local.config_flow.Client", return_value=mock_client),
        patch("custom_components.bestway_spa_local.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "192.0.2.10", "name": "Milan"}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["mac"] == MAC
    assert result["data"]["passcode"] == "synthetic-private-passcode"
    mock_client.async_close.assert_awaited_once()
    await hass.async_block_till_done()


async def test_failed_flow_is_retryable_and_closes_client(hass, mock_client):
    mock_client.async_open.side_effect = TimeoutError
    with patch("custom_components.bestway_spa_local.config_flow.Client", return_value=mock_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data={CONF_HOST: "192.0.2.10"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    mock_client.async_close.assert_awaited_once()


async def test_setup_entities_commands_and_clean_unload(hass, entry, mock_client):
    with patch("custom_components.bestway_spa_local.coordinator.Client", return_value=mock_client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = er.async_get(hass)
        entity_id = registry.async_get_entity_id("climate", DOMAIN, "aabbccddeeff_climate")
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state.state == "heat"
        assert state.attributes["hvac_action"] == "heating"
        reached = registry.async_get_entity_id(
            "binary_sensor", DOMAIN, "aabbccddeeff_target_reached"
        )
        fault = registry.async_get_entity_id("binary_sensor", DOMAIN, "aabbccddeeff_fault")
        assert hass.states.get(reached).state == "on"
        assert hass.states.get(fault).state == "off"
        for key in (
            "current_temperature",
            "target_temperature",
            "heater_state",
            "filter_state",
            "bubbles_level",
        ):
            sensor = registry.async_get_entity_id("sensor", DOMAIN, f"aabbccddeeff_{key}")
            assert sensor is not None
            assert hass.states.get(sensor).state not in ("unknown", "unavailable")
        await hass.services.async_call(
            "climate", "set_hvac_mode", {"entity_id": entity_id, "hvac_mode": "off"}, blocking=True
        )
        mock_client.async_set_values.assert_awaited_with({"heat": False})
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
    mock_client.async_close.assert_awaited()
    assert hass.states.get(entity_id) is None or hass.states.get(entity_id).state == "unavailable"


async def test_failed_setup_closes_client(hass, entry, mock_client):
    mock_client.async_open.side_effect = OSError("offline")
    with patch("custom_components.bestway_spa_local.coordinator.Client", return_value=mock_client):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    mock_client.async_close.assert_awaited()


async def test_duplicate_flow_closes_client(hass, entry, mock_client):
    with patch("custom_components.bestway_spa_local.config_flow.Client", return_value=mock_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data={CONF_HOST: "192.0.2.10"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_client.async_close.assert_awaited_once()


async def test_reconfigure_refuses_a_different_device(hass, entry, mock_client):
    mock_client.identity.mac = "02:00:00:00:00:02"
    with patch("custom_components.bestway_spa_local.config_flow.Client", return_value=mock_client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
            data={CONF_HOST: "192.0.2.20"},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
    assert entry.data[CONF_HOST] == "192.0.2.10"
    mock_client.async_close.assert_awaited_once()


async def test_reconfigure_only_offers_host(hass, entry):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
    )
    assert {key.schema for key in result["data_schema"].schema} == {CONF_HOST}


async def test_device_model_comes_from_verified_profile(hass, entry, mock_client):
    from custom_components.bestway_spa_local.coordinator import BestwayCoordinator
    from custom_components.bestway_spa_local.entity import BestwayEntity

    mock_client.profile.model = "Synthetic future profile"
    with patch("custom_components.bestway_spa_local.coordinator.Client", return_value=mock_client):
        coordinator = BestwayCoordinator(hass, entry)
        entity = BestwayEntity(coordinator, "test")
        assert entity.device_info["model"] == "Synthetic future profile"
        await coordinator.async_shutdown()


async def test_shutdown_clears_repair_when_pending_poll_fails_during_close(
    hass, entry, mock_client
):
    from homeassistant.helpers import issue_registry as ir

    from custom_components.bestway_spa_local.coordinator import BestwayCoordinator

    entered, closed = asyncio.Event(), asyncio.Event()

    async def pending_read():
        entered.set()
        await closed.wait()
        raise OSError("socket closed")

    async def close():
        closed.set()
        await asyncio.sleep(0)

    mock_client.async_read_state.side_effect = pending_read
    mock_client.async_close.side_effect = close
    with patch("custom_components.bestway_spa_local.coordinator.Client", return_value=mock_client):
        coordinator = BestwayCoordinator(hass, entry)
        coordinator.failures = 2
        task = asyncio.create_task(coordinator._async_update_data())
        await entered.wait()
        await coordinator.async_shutdown()
        await asyncio.gather(task, return_exceptions=True)
        assert ir.async_get(hass).async_get_issue(DOMAIN, f"unreachable_{entry.entry_id}") is None


async def test_options_reload_once_without_entry_update_listener(hass, entry, mock_client):
    with patch("custom_components.bestway_spa_local.coordinator.Client", return_value=mock_client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        with patch.object(hass.config_entries, "async_reload", return_value=True) as reload:
            result = await hass.config_entries.options.async_init(entry.entry_id)
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], {"poll_interval": 30}
            )
            await hass.async_block_till_done()
            assert result["type"] is FlowResultType.CREATE_ENTRY
            reload.assert_awaited_once_with(entry.entry_id)
        assert not entry.update_listeners
        await hass.config_entries.async_unload(entry.entry_id)


async def test_diagnostics_exclude_identifiers_and_credentials(hass, entry, mock_client):
    from custom_components.bestway_spa_local.diagnostics import async_get_config_entry_diagnostics

    with patch("custom_components.bestway_spa_local.coordinator.Client", return_value=mock_client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        data = await async_get_config_entry_diagnostics(hass, entry)
        for secret in ("192.0.2.10", MAC, mock_client.passcode, "synthetic-device-id"):
            assert secret not in str(data)
        assert data["raw_status"] == mock_client.last_state.raw.hex()
        await hass.config_entries.async_unload(entry.entry_id)


async def test_shutdown_cancels_inflight_poll_without_control_writes(hass, entry, mock_client):
    from custom_components.bestway_spa_local.coordinator import BestwayCoordinator

    entered = asyncio.Event()

    async def stalled_read():
        entered.set()
        await asyncio.Event().wait()

    mock_client.async_read_state.side_effect = stalled_read
    with patch("custom_components.bestway_spa_local.coordinator.Client", return_value=mock_client):
        coordinator = BestwayCoordinator(hass, entry)
        task = asyncio.create_task(coordinator._async_update_data())
        await entered.wait()
        async with asyncio.timeout(1):
            await coordinator.async_shutdown()
        assert task.cancelled()
        mock_client.async_close.assert_awaited()
        mock_client.async_set_values.assert_not_awaited()


async def test_command_failure_marks_unavailable_and_does_not_retry(hass, entry, mock_client):
    from homeassistant.exceptions import HomeAssistantError

    from custom_components.bestway_spa_local.coordinator import BestwayCoordinator
    from custom_components.bestway_spa_local.protocol import CommandAmbiguousError

    with patch("custom_components.bestway_spa_local.coordinator.Client", return_value=mock_client):
        coordinator = BestwayCoordinator(hass, entry)
        mock_client.async_set_values.side_effect = CommandAmbiguousError("unconfirmed")
        with pytest.raises(HomeAssistantError, match="not retried"):
            await coordinator.async_apply({"heat": False})
        assert not coordinator.last_update_success
        mock_client.async_set_values.assert_awaited_once()
        await coordinator.async_shutdown()


async def test_repeated_failure_backs_off_and_success_clears_repair(hass, entry, mock_client):
    from homeassistant.helpers import issue_registry as ir
    from homeassistant.helpers.update_coordinator import UpdateFailed

    from custom_components.bestway_spa_local.coordinator import BestwayCoordinator

    with patch("custom_components.bestway_spa_local.coordinator.Client", return_value=mock_client):
        coordinator = BestwayCoordinator(hass, entry)
        mock_client.async_open.side_effect = OSError("offline")
        for _ in range(7):
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()
        assert coordinator.update_interval.total_seconds() == 300
        registry = ir.async_get(hass)
        assert registry.async_get_issue(DOMAIN, f"unreachable_{entry.entry_id}") is not None
        mock_client.async_open.side_effect = None
        await coordinator._async_update_data()
        assert coordinator.update_interval.total_seconds() == 15
        assert registry.async_get_issue(DOMAIN, f"unreachable_{entry.entry_id}") is None
        await coordinator.async_shutdown()


async def test_partial_platform_failure_releases_platforms_and_client(hass, entry, mock_client):
    with (
        patch("custom_components.bestway_spa_local.coordinator.Client", return_value=mock_client),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            side_effect=RuntimeError("platform failed"),
        ),
        patch.object(hass.config_entries, "async_unload_platforms", return_value=True) as unload,
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        unload.assert_awaited_once()
        mock_client.async_close.assert_awaited()


async def test_temperature_service_converts_display_units_and_applies_mode(
    hass, entry, mock_client
):
    # HA defaults to Celsius; the physical fixture is Fahrenheit. 37 C -> 98.6 F.
    with patch("custom_components.bestway_spa_local.coordinator.Client", return_value=mock_client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_id = er.async_get(hass).async_get_entity_id(
            "climate", DOMAIN, "aabbccddeeff_climate"
        )
        await hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": entity_id, "temperature": 37, "hvac_mode": "off"},
            blocking=True,
        )
        mock_client.async_set_values.assert_awaited_once_with(
            {"target_temperature": 99, "heat": False}
        )
        await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    "heat,action",
    [(0, "off"), (1, "idle"), (2, "heating"), (3, "idle"), (4, "heating"), (255, None)],
)
async def test_heater_state_codes_and_native_unit_changes(hass, entry, mock_client, heat, action):
    from custom_components.bestway_spa_local.climate import BestwayClimate
    from custom_components.bestway_spa_local.coordinator import BestwayCoordinator

    data = bytearray(mock_client.last_state.raw)
    data[0] |= 2
    data[1] = data[38] = 40
    data[2] = heat
    state = decode_status(b"\x03" + data)
    with patch("custom_components.bestway_spa_local.coordinator.Client", return_value=mock_client):
        coordinator = BestwayCoordinator(hass, entry)
        coordinator.async_set_updated_data(state)
        climate = BestwayClimate(coordinator)
        assert climate.hvac_action == action
        assert climate.temperature_unit == "°C"
        assert (climate.min_temp, climate.max_temp) == (20, 40)
        assert climate.current_temperature == 40
        await coordinator.async_shutdown()
