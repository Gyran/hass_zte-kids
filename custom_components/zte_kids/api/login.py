"""ZTE Kids account login (AES password + signed query)."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any
from urllib.parse import urlencode

import aiohttp

from .client import ZteKidsAuthError, ZteKidsError
from .constants import REGION_KEYS
from .signing import build_sign_string, encrypt_password_plain, sha256_hex

DEFAULT_MOBILE_TYPE = "Generic;Device;Android;14"


async def async_login(
    login_name: str,
    password: str,
    *,
    websession: aiohttp.ClientSession,
    region: str = "international",
    mobile_type: str = DEFAULT_MOBILE_TYPE,
    api_base: str | None = None,
    timeout: float = 30,
) -> dict[str, Any]:
    """
    Perform login and return credentials dict.

    Keys: accesstoken, openid, api_base, region, token_expire_time (optional).
    """
    login_name = login_name.strip()
    region = region.strip().lower()
    if not login_name or not password:
        raise ZteKidsAuthError("Email and password are required", code=None)
    if region not in REGION_KEYS:
        raise ZteKidsError(f"Unknown region: {region!r}")

    keys = REGION_KEYS[region]
    base = (api_base or keys["default_base"]).rstrip("/")

    enc_pw = encrypt_password_plain(password, keys["aes_key"])
    ts = str(int(time.time() * 1000))
    nonce = uuid.uuid4().hex
    body_obj = {
        "loginName": login_name,
        "password": enc_pw,
        "dypwdFlag": "N",
        "mobileType": mobile_type,
    }
    sign_params = {
        **body_obj,
        "timestamp": ts,
        "nonce": nonce,
        "appKey": keys["app_key"],
    }
    sign = sha256_hex(build_sign_string(sign_params, keys["sign_secret_suffix"]))
    url = (
        f"{base}/api/account/login?"
        f"{urlencode({'sign': sign, 'timestamp': ts, 'nonce': nonce, 'appKey': keys['app_key']})}"
    )
    # Exact JSON body matters for server; keep separators stable.
    body = json.dumps(body_obj, separators=(",", ":"), ensure_ascii=False)
    client_timeout = aiohttp.ClientTimeout(total=timeout)

    try:
        async with websession.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            data=body,
            timeout=client_timeout,
        ) as response:
            text = await response.text()
            try:
                payload = json.loads(text) if text else {}
            except json.JSONDecodeError as err:
                raise ZteKidsError(f"Invalid login JSON: {text[:500]}") from err
            status = response.status
    except TimeoutError as err:
        raise ZteKidsError(f"login request timed out: {err}") from err
    except aiohttp.ClientError as err:
        raise ZteKidsError(f"login request failed: {err}") from err

    code = payload.get("code")
    if code in (1022, 1132) or (isinstance(code, int) and code != 0):
        raise ZteKidsAuthError(
            f"login code {code}: {payload.get('msg')}",
            code=code if isinstance(code, int) else None,
        )
    if status >= 400:
        raise ZteKidsError(f"login HTTP {status}: {payload}")

    data = payload.get("data")
    if not isinstance(data, dict):
        raise ZteKidsError(f"login missing data: {payload}")
    token = (data.get("accesstoken") or "").strip()
    openid = (data.get("openid") or "").strip()
    if not token or not openid:
        raise ZteKidsError(f"login missing token/openid: {payload}")

    return {
        "accesstoken": token,
        "openid": openid,
        "api_base": base,
        "region": region,
        "token_expire_time": data.get("token_expire_time"),
    }
