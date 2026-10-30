"""Base entity for ZTE Kids watches."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER
from .coordinator import ZteKidsDataUpdateCoordinator


class ZteKidsEntity(CoordinatorEntity[ZteKidsDataUpdateCoordinator]):
    """Entity tied to one watch imei."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZteKidsDataUpdateCoordinator,
        imei: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._imei = imei
        device = self.device_data
        name = (device.get("name") or imei).strip() or imei
        model = device.get("model") or "Kids Watch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, imei)},
            name=name,
            manufacturer=MANUFACTURER,
            model=str(model),
            serial_number=imei,
        )

    @property
    def device_data(self) -> dict[str, Any]:
        """Return latest device dict for this imei."""
        if not self.coordinator.data:
            return {}
        return self.coordinator.data.get(self._imei, {})

    @property
    def available(self) -> bool:
        """Available when coordinator has this imei."""
        return super().available and self._imei in (self.coordinator.data or {})
