"""Authenticated ZTE Kids API client."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

import aiohttp

from .constants import REGION_KEYS
from .signing import append_signed_query, signed_guard_params

# Token invalid / expired. Login-time codes 1022 / 1132 are handled in login.py.
AUTH_ERROR_CODES = (1002,)


class ZteKidsError(Exception):
    """API returned an error or unexpected payload."""


class ZteKidsAuthError(ZteKidsError):
    """Authentication / token error (e.g. code 1002, 1022, 1132)."""

    def __init__(self, message: str, *, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class ZteKidsClient:
    """Async client using accesstoken / openid / api_base / region."""

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        credentials: dict[str, Any],
        *,
        timeout: float = 30,
    ) -> None:
        self._websession = websession
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self.update_credentials(credentials)

    def update_credentials(self, credentials: dict[str, Any]) -> None:
        """Replace token / openid / base from a credentials dict."""
        self._token = (credentials.get("accesstoken") or "").strip()
        self._openid = (credentials.get("openid") or "").strip()
        self._base = (credentials.get("api_base") or "").rstrip("/")
        region = (credentials.get("region") or "international").strip().lower()
        if region not in REGION_KEYS:
            raise ZteKidsError(f"Unknown region: {region!r}")
        self._region = region
        if not self._token or not self._openid or not self._base:
            raise ZteKidsError(
                "Credentials must include accesstoken, openid, and api_base"
            )

    @property
    def openid(self) -> str:
        return self._openid

    @property
    def accesstoken(self) -> str:
        return self._token

    @property
    def api_base(self) -> str:
        return self._base

    @property
    def region(self) -> str:
        return self._region

    @property
    def websession(self) -> aiohttp.ClientSession:
        """Shared aiohttp session (owned by Home Assistant)."""
        return self._websession

    async def _async_request(
        self, method: str, name: str, url: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Send a request, decode JSON and map API codes to exceptions."""
        try:
            async with self._websession.request(
                method,
                url,
                headers={"Accept": "application/json"},
                timeout=self._timeout,
                **kwargs,
            ) as response:
                text = await response.text()
                try:
                    data = json.loads(text) if text else {}
                except json.JSONDecodeError as err:
                    raise ZteKidsError(f"Invalid JSON: {text[:500]}") from err
                if response.status >= 400:
                    raise ZteKidsError(f"{name} HTTP {response.status}: {data}")
        except TimeoutError as err:
            raise ZteKidsError(f"{name} request timed out: {err}") from err
        except aiohttp.ClientError as err:
            raise ZteKidsError(f"{name} request failed: {err}") from err

        if not isinstance(data, dict):
            raise ZteKidsError(f"{name} unexpected payload: {data}")
        code = data.get("code")
        if code in AUTH_ERROR_CODES:
            raise ZteKidsAuthError(
                f"{name} code {code}: {data.get('msg')}", code=code
            )
        if code != 0:
            raise ZteKidsError(f"{name} code {code}: {data.get('msg')}")
        return data

    async def async_get_related_devices(self) -> dict[str, Any]:
        """GET getway/accounts/{openid}/related-device."""
        url = append_signed_query(
            self._base,
            f"getway/accounts/{self._openid}/related-device",
            query_for_sign={"accesstoken": self._token},
            region=self._region,
        )
        return await self._async_request("GET", "related-device", url)

    async def async_request_location(self, imei: str) -> None:
        """POST getway/devices/{imei}/location/last.

        Asks the watch for a fresh fix. code 0 is success even when the body
        has no lat/lon. Coordinates arrive on a later related-device poll.
        """
        imei = imei.strip()
        body = {
            "imei": imei,
            "openid": self._openid,
            "accesstoken": self._token,
        }
        guard = signed_guard_params(body, region=self._region)
        url = (
            f"{self._base}/getway/devices/{imei}/location/last?"
            f"{urlencode(guard)}"
        )
        await self._async_request("POST", "location/last", url, data=body)

    @staticmethod
    def devices_by_imei(related: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Merge ownedDevices + chatGroupDevices, keyed by imei."""
        out: dict[str, dict[str, Any]] = {}
        for key in ("ownedDevices", "chatGroupDevices"):
            for device in related.get(key) or []:
                imei = device.get("imei")
                if not imei:
                    continue
                out[str(imei).strip()] = device
        return out
