"""Setup, entities, re-login, services and diagnostics."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.zte_kids.api import ZteKidsAuthError
from custom_components.zte_kids.const import DOMAIN
from custom_components.zte_kids.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import IMEI


async def _setup(hass: HomeAssistant, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_creates_entities(hass: HomeAssistant, mock_api, mock_entry) -> None:
    await _setup(hass, mock_entry)
    assert mock_entry.state is ConfigEntryState.LOADED
    ent_reg = er.async_get(hass)
    ids = {e.unique_id for e in er.async_entries_for_config_entry(ent_reg, mock_entry.entry_id)}
    assert ids == {
        f"{IMEI}_tracker",
        f"{IMEI}_battery",
        f"{IMEI}_last_fix",
        f"{IMEI}_online",
        f"{IMEI}_refresh_location",
    }
    battery = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{IMEI}_battery")
    assert hass.states.get(battery).state == "77"
    online = ent_reg.async_get_entity_id("binary_sensor", DOMAIN, f"{IMEI}_online")
    assert hass.states.get(online).state == "on"


async def test_relogin_does_not_reload_entry(
    hass: HomeAssistant, mock_api, mock_entry
) -> None:
    await _setup(hass, mock_entry)
    mock_api["related"].side_effect = [
        ZteKidsAuthError("expired", code=1002),
        {"code": 0, "ownedDevices": []},
    ]
    with patch.object(
        hass.config_entries, "async_reload", wraps=hass.config_entries.async_reload
    ) as reload_spy:
        await mock_entry.runtime_data.coordinator.async_refresh()
        await hass.async_block_till_done()
    assert mock_entry.data["accesstoken"] == "token-2"
    reload_spy.assert_not_called()
    assert mock_entry.state is ConfigEntryState.LOADED


async def test_refresh_service_by_device(hass: HomeAssistant, mock_api, mock_entry) -> None:
    await _setup(hass, mock_entry)
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, IMEI), mock_entry.entry_id
    )
    with patch(
        "custom_components.zte_kids.coordinator.ZteKidsDataUpdateCoordinator.async_request_fresh_location"
    ) as fresh:
        await hass.services.async_call(
            DOMAIN, "refresh_location", {"device_id": device.id}, blocking=True
        )
    fresh.assert_awaited_once_with(IMEI)


async def test_diagnostics_redacts(hass: HomeAssistant, mock_api, mock_entry) -> None:
    await _setup(hass, mock_entry)
    diag = await async_get_config_entry_diagnostics(hass, mock_entry)
    text = str(diag)
    for secret in ("password123", "token-1", "open-1", IMEI, "parent@example.com"):
        assert secret not in text


async def test_unload(hass: HomeAssistant, mock_api, mock_entry) -> None:
    await _setup(hass, mock_entry)
    assert await hass.config_entries.async_unload(mock_entry.entry_id)
    assert not hass.services.has_service(DOMAIN, "refresh_location")
