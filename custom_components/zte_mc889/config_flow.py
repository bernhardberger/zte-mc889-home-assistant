"""Config flow for ZTE MC889 integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_HOST, CONF_PASSWORD, DEFAULT_HOST, DOMAIN
from .zte_api import ZteAuthError, ZteClient, ZteError, ZteLockoutError

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
    vol.Required(CONF_PASSWORD): str,
})


class ZteMC889ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for ZTE MC889 modem."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step — enter host and password."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            password = user_input[CONF_PASSWORD]

            # Prevent duplicate entries for the same host
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Validate credentials by attempting login
            try:
                client = ZteClient(host=host, password=password, timeout=10)
                await self.hass.async_add_executor_job(client.login)
                await self.hass.async_add_executor_job(client.logout)
            except ZteLockoutError:
                errors["base"] = "lockout"
            except ZteAuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error connecting to ZTE MC889")
                errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title=f"ZTE MC889 ({host})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )
