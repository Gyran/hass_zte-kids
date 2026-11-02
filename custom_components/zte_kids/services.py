"""Services for ZTE Kids."""

from __future__ import annotations

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

# Longest suffix first so `_last_fix` is not parsed as a shorter tail.
_UNIQUE_ID_SUFFIXES = (
    "_refresh_location",
    "_last_fix",
    "_tracker",
    "_battery",
    "_online",
)


def _imei_from_unique_id(unique_id: str | None) -> str | None:
    """Return the watch imei stored in an entity unique id."""
    if not unique_id:
        return None
    for suffix in _UNIQUE_ID_SUFFIXES:
        if unique_id.endswith(suffix):
            imei = unique_id[: -len(suffix)]
            return imei or None
    return None


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

    for entity_id in referenced.referenced | referenced.indirectly_referenced:
        entity = ent_reg.async_get(entity_id)
        if (
            entity is None
            or entity.platform != DOMAIN
            or entity.config_entry_id is None
        ):
            continue
        imei = _imei_from_unique_id(entity.unique_id)
        entry = hass.config_entries.async_get_entry(entity.config_entry_id)
        if imei is None or entry is None or entry.domain != DOMAIN:
            continue
        if entry.state != ConfigEntryState.LOADED:
            continue
        found.setdefault(imei, entry)

    dev_reg = dr.async_get(hass)
    for device_id in referenced.referenced_devices:
        device = dev_reg.async_get(device_id)
        if device is None:
            continue
        imei = next(
            (
                identifier
                for domain, identifier in device.identifiers
                if domain == DOMAIN
            ),
            None,
        )
        if imei is None:
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
    for entry, imei in targets:
        await entry.runtime_data.coordinator.async_request_fresh_location(imei)


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
