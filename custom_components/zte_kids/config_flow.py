"""Config flow for ZTE Kids."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    REGION_KEYS,
    ZteKidsAuthError,
    ZteKidsClient,
    ZteKidsError,
    async_login,
)
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
    MIN_SCAN_INTERVAL,
    PASSWORD_MAX_LEN,
    PASSWORD_MIN_LEN,
)

REGION_OPTIONS = [
    selector.SelectOptionDict(value=key, label=key)
    for key in REGION_KEYS
]


class ZteKidsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ZTE Kids."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            password = user_input[CONF_PASSWORD]
            region = user_input.get(CONF_REGION, DEFAULT_REGION)
            scan_interval = int(
                user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            )

            if not PASSWORD_MIN_LEN <= len(password) <= PASSWORD_MAX_LEN:
                errors["base"] = "password_length"
            else:
                websession = async_get_clientsession(self.hass)
                try:
                    credentials = await async_login(
                        email, password, websession=websession, region=region
                    )
                    client = ZteKidsClient(websession, credentials)
                    related = await client.async_get_related_devices()
                    devices = ZteKidsClient.devices_by_imei(related)
                    if not devices:
                        errors["base"] = "no_devices"
                    else:
                        await self.async_set_unique_id(credentials["openid"])
                        self._abort_if_unique_id_configured()
                        return self.async_create_entry(
                            title=email,
                            data={
                                CONF_EMAIL: email,
                                CONF_PASSWORD: password,
                                CONF_REGION: credentials["region"],
                                CONF_ACCESSTOKEN: credentials["accesstoken"],
                                CONF_OPENID: credentials["openid"],
                                CONF_API_BASE: credentials["api_base"],
                            },
                            options={CONF_SCAN_INTERVAL: scan_interval},
                        )
                except ZteKidsAuthError as err:
                    LOGGER.warning("Auth failed during setup: %s", err)
                    if err.code == 1022:
                        errors["base"] = "password_format"
                    else:
                        errors["base"] = "auth"
                except ZteKidsError as err:
                    LOGGER.error("API error during setup: %s", err)
                    errors["base"] = "connection"
                except Exception:  # noqa: BLE001
                    LOGGER.exception("Unexpected error during setup")
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EMAIL,
                        default=(user_input or {}).get(CONF_EMAIL, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.EMAIL,
                        )
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        )
                    ),
                    vol.Required(
                        CONF_REGION,
                        default=(user_input or {}).get(CONF_REGION, DEFAULT_REGION),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=REGION_OPTIONS)
                    ),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=(user_input or {}).get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=3600,
                            step=30,
                            unit_of_measurement="seconds",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Handle reauth when credentials fail."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Dialog to re-enter password.

        Update entry data and abort; add_update_listener reloads.
        (Avoid async_update_reload_and_abort with listeners — warned for 2026.12.)
        """
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            email = reauth_entry.data[CONF_EMAIL]
            region = reauth_entry.data.get(CONF_REGION, DEFAULT_REGION)
            if not PASSWORD_MIN_LEN <= len(password) <= PASSWORD_MAX_LEN:
                errors["base"] = "password_length"
            else:
                websession = async_get_clientsession(self.hass)
                try:
                    credentials = await async_login(
                        email, password, websession=websession, region=region
                    )
                except ZteKidsAuthError as err:
                    LOGGER.warning("Reauth failed: %s", err)
                    errors["base"] = (
                        "password_format" if err.code == 1022 else "auth"
                    )
                except ZteKidsError as err:
                    LOGGER.error("Reauth connection error: %s", err)
                    errors["base"] = "connection"
                else:
                    self.hass.config_entries.async_update_entry(
                        reauth_entry,
                        data={
                            **reauth_entry.data,
                            CONF_PASSWORD: password,
                            CONF_ACCESSTOKEN: credentials["accesstoken"],
                            CONF_OPENID: credentials["openid"],
                            CONF_API_BASE: credentials["api_base"],
                            CONF_REGION: credentials["region"],
                        },
                    )
                    return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        )
                    ),
                }
            ),
            description_placeholders={
                "email": reauth_entry.data.get(CONF_EMAIL, ""),
            },
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ZteKidsOptionsFlow:
        """Return options flow."""
        return ZteKidsOptionsFlow()


class ZteKidsOptionsFlow(config_entries.OptionsFlow):
    """Handle options (scan interval)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                },
            )

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=3600,
                            step=30,
                            unit_of_measurement="seconds",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
        )
