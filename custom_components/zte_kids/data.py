"""Custom types for zte_kids."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .api import ZteKidsClient
    from .coordinator import ZteKidsDataUpdateCoordinator

type ZteKidsConfigEntry = ConfigEntry[ZteKidsData]


@dataclass
class ZteKidsData:
    """Runtime data for one config entry."""

    client: ZteKidsClient
    coordinator: ZteKidsDataUpdateCoordinator
