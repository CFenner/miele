"""Config flow for Miele."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import persistent_notification, zeroconf
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.device_registry import format_mac

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class OAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Config flow to handle Miele OAuth2 authentication."""

    DOMAIN = DOMAIN

    entry = None
    name = None

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    @property
    def extra_authorize_data(self) -> dict:
        """Extra data that needs to be appended to the authorize url."""
        return {
            "vg": "sv_SE",
        }

    async def async_step_reauth(
        self, entry: dict[str, Any] | None = None
    ) -> FlowResult:
        """Perform reauth upon an API authentication error."""
        self.entry = entry
        persistent_notification.async_create(
            self.hass,
            (
                f"Miele integration for account {entry['auth_implementation']} needs to ",
                "be re-authenticated. Please go to the integrations page to re-configure it.",
            ),
            "Miele re-authentication",
            "miele_reauth",
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                description_placeholders={"account": self.entry["auth_implementation"]},
                data_schema=vol.Schema({}),
                errors={},
            )

        persistent_notification.async_dismiss(self.hass, "miele_reauth")
        return await self.async_step_user()

    async def async_oauth_create_entry(self, data: dict) -> FlowResult:
        """Create an oauth config entry or update existing entry for reauth."""
        existing_entry = await self.async_set_unique_id(DOMAIN)
        if existing_entry:
            self.hass.config_entries.async_update_entry(existing_entry, data=data)
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        return await super().async_oauth_create_entry(data)

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
        ) -> FlowResult:
        """Prepare configuration for a Zeroconf discovered Miele device."""
        self.name = discovery_info.name.split(".", 1)[0]
        return await self.async_step_zeroconf_confirm(
            {
                CONF_HOST: discovery_info.host,
                CONF_NAME: self.name,
                CONF_PORT: discovery_info.port,
            }
        )

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by zeroconf."""

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            try:
                return await self.async_step_user()
            except:  # (CannotConnect, ConnectionClosed):
                # Device became network unreachable after discovery.
                # Abort and let discovery find it again later.
                return self.async_abort(reason="cannot_connect")
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={CONF_NAME: self.name},
        )
