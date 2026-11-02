"""Authenticated ZTE Kids API client."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

import aiohttp

from .constants import REGION_KEYS
from .signing import append_signed_query, signed_guard_params


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

    async def async_get_related_devices(self) -> dict[str, Any]:
        """GET getway/accounts/{openid}/related-device."""
        url = append_signed_query(
            self._base,
            f"getway/accounts/{self._openid}/related-device",
            query_for_sign={"accesstoken": self._token},
            region=self._region,
        )
        try:
            async with self._websession.get(
                url,
                headers={"Accept": "application/json"},
                timeout=self._timeout,
            ) as response:
                text = await response.text()
                try:
                    data = json.loads(text) if text else {}
                except json.JSONDecodeError as err:
                    raise ZteKidsError(f"Invalid JSON: {text[:500]}") from err
                if response.status >= 400:
                    raise ZteKidsError(
                        f"related-device HTTP {response.status}: {data}"
                    )
        except TimeoutError as err:
            raise ZteKidsError(f"related-device request timed out: {err}") from err
        except aiohttp.ClientError as err:
            raise ZteKidsError(f"related-device request failed: {err}") from err

        code = data.get("code")
        if code == 1002:
            raise ZteKidsAuthError(
                f"related-device code {code}: {data.get('msg')}", code=1002
            )
        if code != 0:
            raise ZteKidsError(
                f"related-device code {code}: {data.get('msg')}"
            )
        return data

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
        try:
            async with self._websession.post(
                url,
                data=body,
                headers={"Accept": "application/json"},
                timeout=self._timeout,
            ) as response:
                text = await response.text()
                try:
                    data = json.loads(text) if text else {}
                except json.JSONDecodeError as err:
                    raise ZteKidsError(f"Invalid JSON: {text[:500]}") from err
                if response.status >= 400:
                    raise ZteKidsError(
                        f"location/last HTTP {response.status}: {data}"
                    )
        except TimeoutError as err:
            raise ZteKidsError(f"location/last request timed out: {err}") from err
        except aiohttp.ClientError as err:
            raise ZteKidsError(f"location/last request failed: {err}") from err

        if not isinstance(data, dict):
            raise ZteKidsError(f"location/last unexpected payload: {data}")
        code = data.get("code")
        if code == 1002:
            raise ZteKidsAuthError(
                f"location/last code {code}: {data.get('msg')}", code=1002
            )
        if code != 0:
            raise ZteKidsError(f"location/last code {code}: {data.get('msg')}")

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
