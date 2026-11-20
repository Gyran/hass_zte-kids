"""Diagnostics for ZTE Kids."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .const import CONF_ACCESSTOKEN, CONF_OPENID

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import ZteKidsConfigEntry

TO_REDACT_ENTRY = {
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_ACCESSTOKEN,
    CONF_OPENID,
    "unique_id",
    "title",
}
TO_REDACT_DEVICE = {
    "imei",
    "bindNo",
    "name",
    "lat",
    "lon",
    "address",
    "phone",
    "iccid",
    "openid",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ZteKidsConfigEntry,
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT_ENTRY),
        "devices": [
            async_redact_data(device, TO_REDACT_DEVICE)
            for device in (coordinator.data or {}).values()
        ],
    }
