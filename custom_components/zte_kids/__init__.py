"""ZTE Kids custom integration for Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_EMAIL, Platform
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ZteKidsClient
from .const import (
    CONF_ACCESSTOKEN,
    CONF_API_BASE,
    CONF_OPENID,
    CONF_REGION,
    DEFAULT_REGION,
    DOMAIN,
    LOGGER,
)
from .coordinator import ZteKidsDataUpdateCoordinator
from .data import ZteKidsData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import ZteKidsConfigEntry

PLATFORMS: list[Platform] = [
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(
    hass: HomeAssistant, entry: ZteKidsConfigEntry
) -> bool:
    """Set up ZTE Kids from a config entry."""
    credentials = {
        "accesstoken": entry.data[CONF_ACCESSTOKEN],
        "openid": entry.data[CONF_OPENID],
        "api_base": entry.data[CONF_API_BASE],
        "region": entry.data.get(CONF_REGION, DEFAULT_REGION),
    }
    client = ZteKidsClient(async_get_clientsession(hass), credentials)
    coordinator = ZteKidsDataUpdateCoordinator(hass, entry, client)
    entry.runtime_data = ZteKidsData(client=client, coordinator=coordinator)

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    LOGGER.debug(
        "ZTE Kids setup for %s (%s devices)",
        entry.data.get(CONF_EMAIL),
        len(coordinator.data or {}),
    )
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: ZteKidsConfigEntry
) -> None:
    """Reload when options / entry data change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: ZteKidsConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
