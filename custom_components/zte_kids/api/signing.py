"""Match SecurityGuardRequestFilter + ta.f.a (AES password)."""

from __future__ import annotations

import base64
import hashlib
import os
import time
import uuid
from typing import Any
from urllib.parse import urlencode

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .constants import REGION_KEYS


def encrypt_password_plain(plain: str, aes_key: str) -> str:
    """AES/GCM/NoPadding, 12-byte IV, IV || ciphertext+tag, Base64."""
    key = aes_key.encode("utf-8")
    if len(key) not in (16, 24, 32):
        raise ValueError(f"AES key must be 16/24/32 bytes, got {len(key)}")
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plain.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def build_sign_string(params: dict[str, Any], sign_secret_suffix: str) -> str:
    """Sorted key=value&... + secret (no & before secret)."""
    parts: list[str] = []
    for key in sorted(params.keys()):
        val = params[key]
        if val is None:
            continue
        parts.append(f"{key}={val}&")
    return "".join(parts) + sign_secret_suffix


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def append_signed_query(
    base: str,
    path: str,
    *,
    query_for_sign: dict[str, str],
    region: str,
) -> str:
    """GET-style: merge sign params onto URL (SecurityGuardRequestFilter)."""
    rk = REGION_KEYS[region]
    ts = str(int(time.time() * 1000))
    nonce = uuid.uuid4().hex
    merged = {
        **query_for_sign,
        "timestamp": ts,
        "nonce": nonce,
        "appKey": rk["app_key"],
    }
    sign = sha256_hex(build_sign_string(merged, rk["sign_secret_suffix"]))
    out_q = {
        **query_for_sign,
        "sign": sign,
        "timestamp": ts,
        "nonce": nonce,
        "appKey": rk["app_key"],
    }
    return f"{base.rstrip('/')}/{path.lstrip('/')}?{urlencode(out_q)}"
