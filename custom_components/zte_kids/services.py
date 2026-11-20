"""Services for ZTE Kids."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import target as target_helpers

from .const import DOMAIN, SERVICE_REFRESH_LOCATION

if TYPE_CHECKING:
    from .data import ZteKidsConfigEntry

def _imei_from_device(device: dr.DeviceEntry | None) -> str | None:
    """Return the watch imei from a device's identifiers."""
    if device is None:
        return None
    return next(
        (ident for domain, ident in device.identifiers if domain == DOMAIN),
        None,
    )


def _targets_from_call(
    hass: HomeAssistant, call: ServiceCall
) -> list[tuple[ZteKidsConfigEntry, str]]:
    """Resolve a service target to loaded (entry, imei) pairs."""
    selection = target_helpers.TargetSelection(call.data)
    referenced = target_helpers.async_extract_referenced_entity_ids(
        hass, selection
    )
    found: dict[str, ZteKidsConfigEntry] = {}
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)

    for entity_id in referenced.referenced | referenced.indirectly_referenced:
        entity = ent_reg.async_get(entity_id)
        if (
            entity is None
            or entity.platform != DOMAIN
            or entity.config_entry_id is None
        ):
            continue
        imei = (
            _imei_from_device(dev_reg.async_get(entity.device_id))
            if entity.device_id
            else None
        )
        entry = hass.config_entries.async_get_entry(entity.config_entry_id)
        if imei is None or entry is None or entry.domain != DOMAIN:
            continue
        if entry.state != ConfigEntryState.LOADED:
            continue
        found.setdefault(imei, entry)

    for device_id in referenced.referenced_devices:
        device = dev_reg.async_get(device_id)
        imei = _imei_from_device(device)
        if device is None or imei is None:
            continue
        entry = hass.config_entries.async_get_entry(device.config_entry_id)
        if entry is None or entry.domain != DOMAIN:
            continue
        if entry.state != ConfigEntryState.LOADED:
            continue
        found.setdefault(imei, entry)

    return [(found[imei], imei) for imei in sorted(found)]


async def async_handle_refresh_location(call: ServiceCall) -> None:
    """Ask each targeted watch for a fresh fix."""
    targets = _targets_from_call(call.hass, call)
    if not targets:
        raise ServiceValidationError(
            "No ZTE Kids watches found for this target"
        )
    results = await asyncio.gather(
        *(
            entry.runtime_data.coordinator.async_request_fresh_location(imei)
            for entry, imei in targets
        ),
        return_exceptions=True,
    )
    for result in results:
        if isinstance(result, BaseException):
            raise result


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_REFRESH_LOCATION):
        return
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_LOCATION,
        async_handle_refresh_location,
        schema=cv.make_entity_service_schema(None),
    )


@callback
def async_unload_services(hass: HomeAssistant, entry_id: str) -> None:
    """Remove services when the last config entry unloads."""
    if any(
        other.entry_id != entry_id and other.state == ConfigEntryState.LOADED
        for other in hass.config_entries.async_entries(DOMAIN)
    ):
        return
    if hass.services.has_service(DOMAIN, SERVICE_REFRESH_LOCATION):
        hass.services.async_remove(DOMAIN, SERVICE_REFRESH_LOCATION)
