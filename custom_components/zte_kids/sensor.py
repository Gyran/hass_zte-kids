"""Sensor platform for ZTE Kids."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.util import dt as dt_util

from .coordinator import location_fix_epoch
from .entity import ZteKidsEntity, setup_per_watch

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import ZteKidsDataUpdateCoordinator
    from .data import ZteKidsConfigEntry

BATTERY_DESCRIPTION = SensorEntityDescription(
    key="battery",
    translation_key="battery",
    device_class=SensorDeviceClass.BATTERY,
    native_unit_of_measurement=PERCENTAGE,
    state_class=SensorStateClass.MEASUREMENT,
)

LAST_FIX_DESCRIPTION = SensorEntityDescription(
    key="last_fix",
    translation_key="last_fix",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZteKidsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up battery and last-fix sensors."""
    setup_per_watch(
        entry,
        async_add_entities,
        lambda c, i: [
            ZteKidsBatterySensor(c, i, BATTERY_DESCRIPTION),
            ZteKidsLastFixSensor(c, i, LAST_FIX_DESCRIPTION),
        ],
    )


class ZteKidsBatterySensor(ZteKidsEntity, SensorEntity):
    """Battery percent for one watch."""

    def __init__(
        self,
        coordinator: ZteKidsDataUpdateCoordinator,
        imei: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, imei)
        self.entity_description = description
        self._attr_unique_id = f"{imei}_{description.key}"

    @property
    def native_value(self) -> int | None:
        """Return battery percent."""
        battery = self.device_data.get("battery") or {}
        percent = battery.get("percent")
        if percent is None:
            return None
        try:
            return int(percent)
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Battery update time when present."""
        battery = self.device_data.get("battery") or {}
        update_time = battery.get("updateTime")
        if update_time is None:
            return {}
        return {"battery_update_time": update_time}


class ZteKidsLastFixSensor(ZteKidsEntity, SensorEntity):
    """Diagnostic timestamp of lastLocation for one watch."""

    def __init__(
        self,
        coordinator: ZteKidsDataUpdateCoordinator,
        imei: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, imei)
        self.entity_description = description
        self._attr_unique_id = f"{imei}_{description.key}"

    @property
    def native_value(self) -> datetime | None:
        """Return the last fix as a timezone-aware datetime."""
        ts = location_fix_epoch(self.device_data)
        if ts is None:
            return None
        return dt_util.utc_from_timestamp(ts)
