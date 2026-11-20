"""Shared fixtures for ZTE Kids tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zte_kids.const import (
    CONF_ACCESSTOKEN,
    CONF_API_BASE,
    CONF_OPENID,
    CONF_REGION,
    DOMAIN,
)

IMEI = "860000000000001"

CREDENTIALS = {
    "accesstoken": "token-1",
    "openid": "open-1",
    "api_base": "https://care-api.nubia.com",
    "region": "international",
}

RELATED = {
    "code": 0,
    "ownedDevices": [
        {
            "imei": IMEI,
            "name": "Kid",
            "model": "Z1",
            "bindNo": "b1",
            "onlineStatus": 1,
            "battery": {"percent": 77, "updateTime": 1},
            "lastLocation": {
                "lat": 59.3,
                "lon": 18.0,
                "radius": 25,
                "timestamp": 1_700_000_000_000,
            },
        }
    ],
}


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Let HA load custom_components/zte_kids."""


@pytest.fixture
def mock_entry() -> MockConfigEntry:
    """A config entry with stored credentials."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="open-1",
        title="parent@example.com",
        data={
            CONF_EMAIL: "parent@example.com",
            CONF_PASSWORD: "password123",
            CONF_REGION: "international",
            CONF_ACCESSTOKEN: "token-1",
            CONF_OPENID: "open-1",
            CONF_API_BASE: "https://care-api.nubia.com",
        },
    )


@pytest.fixture
def mock_api():
    """Patch the network layer: login, related-device, location request."""
    with (
        patch(
            "custom_components.zte_kids.config_flow.async_login",
            AsyncMock(return_value=dict(CREDENTIALS)),
        ) as login_flow,
        patch(
            "custom_components.zte_kids.coordinator.async_login",
            AsyncMock(return_value={**CREDENTIALS, "accesstoken": "token-2"}),
        ) as login_coord,
        patch(
            "custom_components.zte_kids.api.client.ZteKidsClient.async_get_related_devices",
            AsyncMock(return_value=RELATED),
        ) as related,
        patch(
            "custom_components.zte_kids.api.client.ZteKidsClient.async_request_location",
            AsyncMock(return_value=None),
        ) as location,
    ):
        yield {
            "login_flow": login_flow,
            "login_coord": login_coord,
            "related": related,
            "location": location,
        }
