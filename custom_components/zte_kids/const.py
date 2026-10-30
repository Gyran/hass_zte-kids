"""Constants for zte_kids."""

from __future__ import annotations

from logging import Logger, getLogger
from typing import Final

LOGGER: Logger = getLogger(__package__)

DOMAIN: Final[str] = "zte_kids"
ATTRIBUTION: Final[str] = "Data provided by ZTE Kids (Nubia Care API)"

CONF_REGION: Final[str] = "region"
CONF_SCAN_INTERVAL: Final[str] = "scan_interval"
CONF_ACCESSTOKEN: Final[str] = "accesstoken"
CONF_OPENID: Final[str] = "openid"
CONF_API_BASE: Final[str] = "api_base"

DEFAULT_REGION: Final[str] = "international"
DEFAULT_SCAN_INTERVAL: Final[int] = 300
MIN_SCAN_INTERVAL: Final[int] = 60

PASSWORD_MIN_LEN: Final[int] = 8
PASSWORD_MAX_LEN: Final[int] = 16

MANUFACTURER: Final[str] = "Nubia / ZTE"
