"""Config flow for the Yorkshire Water integration."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import CookieJar
from .pyyorkshirewater.auth import YorkshireWaterAuth
from .pyyorkshirewater.exceptions import ApiError, AuthError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_ACCOUNT_NUMBER, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): selector.TextSelector(),
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_ACCOUNT_NUMBER): selector.TextSelector(),
    }
)


class YorkshireWaterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yorkshire Water."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            auth = YorkshireWaterAuth(
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                session=async_create_clientsession(
                    self.hass,
                    cookie_jar=CookieJar(),
                ),
            )

            # Validate credentials
            try:
                await auth.login()
            except AuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception during login")
                errors["base"] = "unknown"

            if not errors:
                # Validate account has a smart meter
                try:
                    from .pyyorkshirewater.api import API

                    api = API(auth)
                    await api.get_meter_details(user_input[CONF_ACCOUNT_NUMBER])
                except ApiError:
                    errors["base"] = "smart_meter_unavailable"
                except Exception:
                    _LOGGER.exception("Unexpected exception during meter validation")
                    errors["base"] = "cannot_connect"

            if not errors:
                await self.async_set_unique_id(user_input[CONF_ACCOUNT_NUMBER])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_ACCOUNT_NUMBER],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
