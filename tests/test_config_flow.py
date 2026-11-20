"""Config, reauth and options flow tests."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.zte_kids.api import ZteKidsAuthError
from custom_components.zte_kids.const import CONF_REGION, CONF_SCAN_INTERVAL, DOMAIN

USER = {
    CONF_EMAIL: "parent@example.com",
    CONF_PASSWORD: "password123",
    CONF_REGION: "international",
    CONF_SCAN_INTERVAL: 300,
}


async def test_user_flow_creates_entry(hass: HomeAssistant, mock_api) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["accesstoken"] == "token-1"


async def test_user_flow_bad_password_length(hass: HomeAssistant, mock_api) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER, CONF_PASSWORD: "short"}
    )
    assert result["errors"] == {"base": "password_length"}


async def test_user_flow_auth_error(hass: HomeAssistant, mock_api) -> None:
    mock_api["login_flow"].side_effect = ZteKidsAuthError("bad", code=1001)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER
    )
    assert result["errors"] == {"base": "auth"}


async def test_user_flow_no_devices(hass: HomeAssistant, mock_api) -> None:
    mock_api["related"].return_value = {"code": 0}
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER
    )
    assert result["errors"] == {"base": "no_devices"}


async def test_reauth_updates_and_reloads(
    hass: HomeAssistant, mock_api, mock_entry
) -> None:
    mock_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    mock_api["login_flow"].return_value = {
        "accesstoken": "token-9",
        "openid": "open-1",
        "api_base": "https://care-api.nubia.com",
        "region": "international",
    }
    result = await mock_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "newpassword1"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_entry.data["accesstoken"] == "token-9"
    assert mock_entry.data[CONF_PASSWORD] == "newpassword1"


async def test_options_flow(hass: HomeAssistant, mock_api, mock_entry) -> None:
    mock_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(mock_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 120}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_entry.options[CONF_SCAN_INTERVAL] == 120
