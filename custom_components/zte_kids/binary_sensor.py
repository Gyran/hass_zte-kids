"""Binary sensor platform for ZTE Kids."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .entity import ZteKidsEntity, setup_per_watch

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
    hass: HomeAssistant,
    entry: ZteKidsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up online binary sensors."""
    setup_per_watch(
        entry,
        async_add_entities,
        lambda c, i: [ZteKidsOnlineBinarySensor(c, i, ONLINE_DESCRIPTION)],
    )


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
    def is_on(self) -> bool | None:
        """Return True when onlineStatus is 1, None when the field is absent."""
        status = self.device_data.get("onlineStatus")
        if status is None:
            return None
        return status == 1
