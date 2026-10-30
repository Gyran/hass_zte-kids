"""Device tracker platform for ZTE Kids."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity

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
    """Set up device trackers for each watch."""
    coordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    def _add_new() -> None:
        if not coordinator.data:
            return
        new: list[ZteKidsTracker] = []
        for imei in coordinator.data:
            if imei in known:
                continue
            known.add(imei)
            new.append(ZteKidsTracker(coordinator, imei))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ZteKidsTracker(ZteKidsEntity, TrackerEntity):
    """Track one watch location from related-device lastLocation."""

    # Entity name = device name (typical device_tracker).
    _attr_name = None

    def __init__(
        self, coordinator: ZteKidsDataUpdateCoordinator, imei: str
    ) -> None:
        """Initialize tracker."""
        super().__init__(coordinator, imei)
        self._attr_unique_id = f"{imei}_tracker"

    @property
    def source_type(self) -> SourceType:
        """Return GPS source type."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return latitude."""
        loc = self.device_data.get("lastLocation") or {}
        return _as_float(loc.get("lat"))

    @property
    def longitude(self) -> float | None:
        """Return longitude."""
        loc = self.device_data.get("lastLocation") or {}
        return _as_float(loc.get("lon"))

    @property
    def location_accuracy(self) -> float:
        """Return accuracy in meters."""
        loc = self.device_data.get("lastLocation") or {}
        accuracy = _as_float(loc.get("radius"))
        return accuracy if accuracy is not None else 0.0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Extra attributes from lastLocation / device."""
        loc = self.device_data.get("lastLocation") or {}
        attrs: dict[str, Any] = {
            "imei": self._imei,
            "bind_no": self.device_data.get("bindNo"),
            "model": self.device_data.get("model"),
            "loc_type": loc.get("loc_type"),
            "location_timestamp": loc.get("timestamp"),
            "address": loc.get("address") or None,
        }
        return {k: v for k, v in attrs.items() if v is not None and v != ""}
