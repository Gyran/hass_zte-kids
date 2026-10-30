#!/usr/bin/env python3
"""Manual check: login + related-device via integration client (no Home Assistant).

  .venv-ha/bin/python tests/manual/probe_api.py

Needs .env: NUBIA_EMAIL, NUBIA_PASSWORD (optional NUBIA_REGION).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


async def _async_main() -> int:
    _load_dotenv()
    email = os.environ.get("NUBIA_EMAIL", "").strip()
    password = os.environ.get("NUBIA_PASSWORD", "")
    region = os.environ.get("NUBIA_REGION", "international").strip() or "international"
    if not email or not password:
        print("Set NUBIA_EMAIL and NUBIA_PASSWORD in .env", file=sys.stderr)
        return 1

    sys.path.insert(0, str(ROOT / "custom_components" / "zte_kids"))
    from api import ZteKidsClient, async_login  # noqa: E402

    async with aiohttp.ClientSession() as websession:
        credentials = await async_login(
            email, password, websession=websession, region=region
        )
        client = ZteKidsClient(websession, credentials)
        related = await client.async_get_related_devices()
        devices = ZteKidsClient.devices_by_imei(related)

    out = {
        "openid": credentials["openid"],
        "api_base": credentials["api_base"],
        "region": credentials["region"],
        "devices": [],
    }
    for imei, device in devices.items():
        loc = device.get("lastLocation") or {}
        bat = device.get("battery") or {}
        out["devices"].append(
            {
                "imei": imei,
                "name": (device.get("name") or "").strip(),
                "lat": loc.get("lat"),
                "lon": loc.get("lon"),
                "radius": loc.get("radius"),
                "loc_type": loc.get("loc_type"),
                "timestamp": loc.get("timestamp"),
                "battery": bat.get("percent"),
                "online": device.get("onlineStatus"),
            }
        )
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    return asyncio.run(_async_main())


if __name__ == "__main__":
    raise SystemExit(main())
