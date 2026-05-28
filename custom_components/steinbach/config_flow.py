"""Config flow for the Steinbach Pool integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api.client import TuyaOpenAPIClient
from .api.error import AuthenticationError
from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_REGION,
    DEFAULT_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    TUYA_ENDPOINTS,
)

_LOGGER = logging.getLogger(__name__)

_REGION_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=list(TUYA_ENDPOINTS),
        mode=SelectSelectorMode.DROPDOWN,
        translation_key="region",
    )
)


def _user_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_ACCESS_ID, default=defaults.get(CONF_ACCESS_ID, "")
            ): str,
            vol.Required(CONF_ACCESS_SECRET): str,
            vol.Required(
                CONF_REGION, default=defaults.get(CONF_REGION, DEFAULT_REGION)
            ): _REGION_SELECTOR,
        }
    )


async def _validate(hass: HomeAssistant, data: Mapping[str, Any]) -> None:
    """Validate credentials by fetching a token and the linked device list."""
    client = TuyaOpenAPIClient(
        data[CONF_ACCESS_ID],
        data[CONF_ACCESS_SECRET],
        data.get(CONF_REGION, DEFAULT_REGION),
    )
    try:
        await hass.async_add_executor_job(client.authenticate)
        await hass.async_add_executor_job(client.get_devices)
    finally:
        await hass.async_add_executor_job(client.close)


class SteinbachConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Steinbach Pool."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Prompt for the Tuya project credentials and validate them."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_ACCESS_ID])
            self._abort_if_unique_id_configured()

            errors = await self._try_validate(user_input)
            if not errors:
                return self.async_create_entry(
                    title="Steinbach Pool",
                    data={
                        CONF_ACCESS_ID: user_input[CONF_ACCESS_ID],
                        CONF_ACCESS_SECRET: user_input[CONF_ACCESS_SECRET],
                        CONF_REGION: user_input[CONF_REGION],
                    },
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
                )

        return self.async_show_form(
            step_id="user", data_schema=_user_schema(user_input or {}), errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when the token/credentials stop working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Prompt for fresh credentials and update the existing entry."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {**entry.data, **user_input}
            errors = await self._try_validate(data)
            if not errors:
                return self.async_update_reload_and_abort(entry, data=data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_user_schema(user_input or entry.data),
            errors=errors,
        )

    async def _try_validate(self, data: Mapping[str, Any]) -> dict[str, str]:
        try:
            await _validate(self.hass, data)
        except AuthenticationError:
            return {"base": "invalid_auth"}
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error validating Steinbach credentials")
            return {"base": "cannot_connect"}
        return {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlow):
    """Handle options (poll interval) for the Steinbach Pool integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the poll interval."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        data_schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)
