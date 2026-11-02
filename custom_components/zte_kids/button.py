"""Button to ask one watch for a fresh GPS fix."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity

from .entity import ZteKidsEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import ZteKidsDataUpdateCoordinator
    from .data import ZteKidsConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ZteKidsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a refresh button for each watch."""
    coordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    def _add_new() -> None:
        if not coordinator.data:
            return
        new: list[ZteKidsRefreshLocationButton] = []
        for imei in coordinator.data:
            if imei in known:
                continue
            known.add(imei)
            new.append(ZteKidsRefreshLocationButton(coordinator, imei))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class ZteKidsRefreshLocationButton(ZteKidsEntity, ButtonEntity):
    """POST location/last, then poll until the fix timestamp moves."""

    _attr_translation_key = "refresh_location"
    _attr_icon = "mdi:crosshairs-gps"

    def __init__(
        self, coordinator: ZteKidsDataUpdateCoordinator, imei: str
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, imei)
        self._attr_unique_id = f"{imei}_refresh_location"

    async def async_press(self) -> None:
        """Ask this watch for a new fix."""
        await self.coordinator.async_request_fresh_location(self._imei)
