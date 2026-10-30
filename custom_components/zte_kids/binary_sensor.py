"""Binary sensor platform for ZTE Kids."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .entity import ZteKidsEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import ZteKidsDataUpdateCoordinator
    from .data import ZteKidsConfigEntry

ONLINE_DESCRIPTION = BinarySensorEntityDescription(
    key="online",
    translation_key="online",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ZteKidsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up online binary sensors."""
    coordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    def _add_new() -> None:
        if not coordinator.data:
            return
        new: list[ZteKidsOnlineBinarySensor] = []
        for imei in coordinator.data:
            if imei in known:
                continue
            known.add(imei)
            new.append(
                ZteKidsOnlineBinarySensor(
                    coordinator, imei, ONLINE_DESCRIPTION
                )
            )
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class ZteKidsOnlineBinarySensor(ZteKidsEntity, BinarySensorEntity):
    """Online status for one watch."""

    def __init__(
        self,
        coordinator: ZteKidsDataUpdateCoordinator,
        imei: str,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, imei)
        self.entity_description = description
        self._attr_unique_id = f"{imei}_{description.key}"

    @property
    def is_on(self) -> bool:
        """Return True when onlineStatus is 1."""
        return self.device_data.get("onlineStatus") == 1
