"""Base entity for ZTE Kids watches."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER
from .coordinator import ZteKidsDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.entity import Entity
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import ZteKidsConfigEntry


def setup_per_watch(
    entry: ZteKidsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    factory: Callable[[ZteKidsDataUpdateCoordinator, str], list[Entity]],
) -> None:
    """Add entities for every watch now and for watches paired later."""
    coordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    def _add_new() -> None:
        new: list[Entity] = []
        for imei in coordinator.data or {}:
            if imei in known:
                continue
            known.add(imei)
            new.extend(factory(coordinator, imei))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


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
