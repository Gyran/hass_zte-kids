"""DataUpdateCoordinator for zte_kids."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from time import monotonic
from typing import Any

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ZteKidsAuthError, ZteKidsClient, ZteKidsError, async_login
from .const import (
    CONF_ACCESSTOKEN,
    CONF_API_BASE,
    CONF_OPENID,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    DEFAULT_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
)
from .data import ZteKidsConfigEntry

_LOCATION_MS_THRESHOLD = 1_000_000_000_000


def location_fix_epoch(device: dict[str, Any]) -> float | None:
    """Unix seconds for lastLocation.timestamp.

    Values with 13 digits (above 1e12) are milliseconds.
    """
    loc = device.get("lastLocation") or {}
    raw = loc.get("timestamp")
    if raw is None or raw == "":
        return None
    try:
        ts = float(raw)
    except (TypeError, ValueError):
        return None
    if ts > _LOCATION_MS_THRESHOLD:
        ts /= 1000.0
    return ts


class ZteKidsDataUpdateCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Fetch related devices; key data by imei."""

    config_entry: ZteKidsConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ZteKidsConfigEntry,
        client: ZteKidsClient,
    ) -> None:
        """Initialize."""
        scan_interval = int(
            config_entry.options.get(
                CONF_SCAN_INTERVAL,
                config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        )
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
            always_update=False,
        )
        self.client = client
        self._login_lock = asyncio.Lock()

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Poll related-device; re-login once on invalid token."""
        stale = self.client.accesstoken
        try:
            return await self._async_fetch_devices()
        except ZteKidsAuthError as err:
            LOGGER.warning("Token invalid (%s); re-login", err)
            try:
                await self._async_relogin(stale)
                return await self._async_fetch_devices()
            except ZteKidsAuthError as auth_err:
                raise ConfigEntryAuthFailed(auth_err) from auth_err
            except ZteKidsError as api_err:
                raise UpdateFailed(api_err) from api_err
        except ZteKidsError as err:
            raise UpdateFailed(err) from err

    async def _async_fetch_devices(self) -> dict[str, dict[str, Any]]:
        """Poll related-device. An empty watch list is success, not a failure."""
        related = await self.client.async_get_related_devices()
        return ZteKidsClient.devices_by_imei(related)

    async def async_request_fresh_location(self, imei: str) -> None:
        """Ask one watch for a fix, then poll until its timestamp moves.

        Gives up after about 24 seconds. An unchanged timestamp is a warning,
        not a failure. The watch may be offline or slow.
        """
        before = location_fix_epoch((self.data or {}).get(imei) or {})
        await self._async_request_location(imei)
        deadline = monotonic() + 24
        while monotonic() < deadline:
            await asyncio.sleep(8)
            await self.async_refresh()
            after = location_fix_epoch((self.data or {}).get(imei) or {})
            if after is not None and after != before:
                return
        LOGGER.warning(
            "Location refresh for %s: timestamp unchanged", imei
        )

    async def _async_request_location(self, imei: str) -> None:
        """POST location/last, re-login once on an invalid token."""
        stale = self.client.accesstoken
        try:
            await self.client.async_request_location(imei)
        except ZteKidsAuthError as err:
            LOGGER.warning(
                "Token invalid during location refresh (%s); re-login", err
            )
            try:
                await self._async_relogin(stale)
                await self.client.async_request_location(imei)
            except ZteKidsAuthError as auth_err:
                raise ConfigEntryAuthFailed(auth_err) from auth_err
            except ZteKidsError as api_err:
                raise UpdateFailed(api_err) from api_err
        except ZteKidsError as err:
            raise UpdateFailed(err) from err

    async def _async_relogin(self, stale_token: str | None = None) -> None:
        """Login with stored credentials and persist new session.

        Serialized. When another caller already replaced the token that failed
        (``stale_token``), the new token is reused instead of logging in again.
        """
        async with self._login_lock:
            if stale_token is not None and self.client.accesstoken != stale_token:
                return
            await self._async_login_and_store()

    async def _async_login_and_store(self) -> None:
        data = self.config_entry.data
        credentials = await async_login(
            data[CONF_EMAIL],
            data[CONF_PASSWORD],
            websession=self.client.websession,
            region=data.get(CONF_REGION, DEFAULT_REGION),
            api_base=data.get(CONF_API_BASE),
        )
        self.client.update_credentials(credentials)
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                **data,
                CONF_ACCESSTOKEN: credentials["accesstoken"],
                CONF_OPENID: credentials["openid"],
                CONF_API_BASE: credentials["api_base"],
                CONF_REGION: credentials["region"],
            },
        )
