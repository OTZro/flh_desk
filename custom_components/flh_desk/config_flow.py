"""Config flow for FLH Desk integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, SERVICE_UUID

_LOGGER = logging.getLogger(__name__)


class FLHDeskConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FLH Desk."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}
        self._discovered_device: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle Bluetooth discovery."""
        _LOGGER.debug("Discovered FLH Desk: %s", discovery_info.address)
        
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        
        self._discovered_device = discovery_info
        
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        assert self._discovered_device is not None
        
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered_device.name or "FLH Desk",
                data={},
            )
        
        self._set_confirm_only()
        
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "name": self._discovered_device.name or "FLH Desk",
                "address": self._discovered_device.address,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user-initiated setup."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=f"FLH Desk {address[-5:]}",
                data=user_input,
            )
        
        # Scan for devices
        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass):
            if (
                discovery_info.address in current_addresses
                or discovery_info.address in self._discovered_devices
            ):
                continue
            
            # Check if it's an FLH Desk (has our service UUID)
            if SERVICE_UUID.lower() in [
                str(uuid).lower() for uuid in discovery_info.service_uuids
            ]:
                self._discovered_devices[discovery_info.address] = discovery_info
        
        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")
        
        # Create selection schema
        devices = {
            address: f"{info.name or 'FLH Desk'} ({address})"
            for address, info in self._discovered_devices.items()
        }
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDRESS): vol.In(devices),
            }),
        )
