#!/usr/bin/env python3
"""Manual smoke: against an already-running local HA, onboard + add zte_kids.

Not part of normal HA develop scripts. Prefer UI setup; use this only to
automate a local config-flow check.

  scripts/develop   # terminal 1
  .venv-ha/bin/python tests/manual/smoke_add_integration.py

Needs .env: HA_PASSWORD, NUBIA_EMAIL, NUBIA_PASSWORD (optional HA_USERNAME).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "http://127.0.0.1:8123"
CLIENT_ID = f"{BASE}/"


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


def _ha_credentials() -> tuple[str, str]:
    """Local HA UI user from env (never hardcode passwords in git)."""
    user = os.environ.get("HA_USERNAME", "admin").strip() or "admin"
    password = os.environ.get("HA_PASSWORD", "").strip()
    if not password:
        raise SystemExit(
            "Set HA_PASSWORD in .env (and optional HA_USERNAME) for local bootstrap."
        )
    return user, password


def _http_json(
    method: str,
    path: str,
    body: dict | None = None,
    token: str | None = None,
) -> tuple[int, object]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8")
        try:
            payload: object = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = raw
        return err.code, payload


def _http_form(path: str, form: dict[str, str]) -> tuple[int, object]:
    data = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8")
        try:
            payload: object = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = raw
        return err.code, payload


def wait_for_ha(timeout: float = 180) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, _ = _http_json("GET", "/api/onboarding")
            if status == 200:
                print("HA is up")
                return
        except Exception:
            pass
        time.sleep(2)
    raise SystemExit("Timed out waiting for Home Assistant on :8123")


def onboarding_done_steps() -> set[str]:
    status, payload = _http_json("GET", "/api/onboarding")
    if status != 200:
        return set()
    if isinstance(payload, list):
        return {item["step"] for item in payload if item.get("done")}
    if isinstance(payload, dict):
        return set(payload.get("done") or [])
    return set()


def token_from_code(code: str) -> str:
    st, resp = _http_form(
        "/auth/token",
        {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": CLIENT_ID,
        },
    )
    if st != 200 or not isinstance(resp, dict) or not resp.get("access_token"):
        raise SystemExit(f"token exchange failed: {st} {resp}")
    return str(resp["access_token"])


def login_password() -> str:
    user, password = _ha_credentials()
    st, flow = _http_json(
        "POST",
        "/auth/login_flow",
        {
            "client_id": CLIENT_ID,
            "handler": ["homeassistant", None],
            "redirect_uri": CLIENT_ID,
        },
    )
    if st != 200 or not isinstance(flow, dict):
        raise SystemExit(f"login_flow failed: {st} {flow}")
    flow_id = flow["flow_id"]
    st, result = _http_json(
        "POST",
        f"/auth/login_flow/{flow_id}",
        {"client_id": CLIENT_ID, "username": user, "password": password},
    )
    if st != 200 or not isinstance(result, dict) or not result.get("result"):
        raise SystemExit(f"login submit failed: {st} {result}")
    return token_from_code(str(result["result"]))


def ensure_auth() -> str:
    user, password = _ha_credentials()
    done = onboarding_done_steps()
    if "user" not in done:
        print(f"Creating onboarding user {user!r}")
        st, resp = _http_json(
            "POST",
            "/api/onboarding/users",
            {
                "client_id": CLIENT_ID,
                "name": "Dev",
                "username": user,
                "password": password,
                "language": "en",
            },
        )
        if st not in (200, 201) or not isinstance(resp, dict) or not resp.get("auth_code"):
            # Maybe already created
            print("onboarding user response", st, resp)
            return login_password()
        token = token_from_code(str(resp["auth_code"]))
    else:
        token = login_password()

    done = onboarding_done_steps()
    for step, path, body in (
        ("core_config", "/api/onboarding/core_config", {}),
        ("analytics", "/api/onboarding/analytics", {}),
        ("integration", "/api/onboarding/integration", {}),
    ):
        if step not in done:
            st, resp = _http_json("POST", path, body, token=token)
            print(f"onboarding {step}: {st}")
    return token


def ensure_nubia_entry(token: str) -> None:
    _load_dotenv()
    email = os.environ.get("NUBIA_EMAIL", "").strip()
    password = os.environ.get("NUBIA_PASSWORD", "")
    region = os.environ.get("NUBIA_REGION", "international").strip() or "international"
    if not email or not password:
        raise SystemExit("Missing NUBIA_EMAIL / NUBIA_PASSWORD in .env")

    st, entries = _http_json("GET", "/api/config/config_entries/entry", token=token)
    if st == 200 and isinstance(entries, list):
        for entry in entries:
            if entry.get("domain") == "zte_kids":
                print("zte_kids entry already present:", entry.get("title"))
                return

    print("Starting zte_kids config flow…")
    st, flow = _http_json(
        "POST",
        "/api/config/config_entries/flow",
        {"handler": "zte_kids", "show_advanced_options": False},
        token=token,
    )
    if st != 200 or not isinstance(flow, dict):
        raise SystemExit(f"config flow start failed: {st} {flow}")
    flow_id = flow["flow_id"]
    st, result = _http_json(
        "POST",
        f"/api/config/config_entries/flow/{flow_id}",
        {
            "email": email,
            "password": password,
            "region": region,
            "scan_interval": 120,
        },
        token=token,
    )
    print("config flow result", st, result)
    if not (isinstance(result, dict) and result.get("type") == "create_entry"):
        raise SystemExit("Failed to create zte_kids entry")


def print_entities(token: str) -> int:
    time.sleep(8)
    st, states = _http_json("GET", "/api/states", token=token)
    if st != 200 or not isinstance(states, list):
        print("states fetch failed", st, states)
        return 1

    hits = []
    for s in states:
        attrs = s.get("attributes") or {}
        blob = json.dumps(s).lower()
        if attrs.get("imei") or "nubia" in blob or "selma" in blob:
            hits.append(s)

    print(f"Found {len(hits)} nubia-related entities")
    for s in hits:
        attrs = s.get("attributes") or {}
        print(
            s.get("entity_id"),
            s.get("state"),
            {
                k: attrs.get(k)
                for k in ("latitude", "longitude", "gps_accuracy", "imei", "battery_level")
                if attrs.get(k) is not None
            },
        )

    if hits:
        return 0
    trackers = [
        s.get("entity_id")
        for s in states
        if str(s.get("entity_id", "")).startswith("device_tracker.")
    ]
    print("no nubia entities yet; device_trackers:", trackers)
    return 1


def main() -> int:
    _load_dotenv()
    wait_for_ha()
    token = ensure_auth()
    print("Authenticated")
    ensure_nubia_entry(token)
    return print_entities(token)


if __name__ == "__main__":
    raise SystemExit(main())
