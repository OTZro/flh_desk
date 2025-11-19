"""Sensor platform for FLH Desk."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import FLHDeskCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FLH Desk sensor platform."""
    coordinator: FLHDeskCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([
        FLHDeskHeightSensor(coordinator, entry),
        FLHDeskConnectionSensor(coordinator, entry),
    ])


class FLHDeskHeightSensor(CoordinatorEntity[FLHDeskCoordinator], SensorEntity):
    """Sensor for current desk height."""

    _attr_has_entity_name = True
    _attr_name = "Height"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS

    def __init__(
        self,
        coordinator: FLHDeskCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{entry.unique_id}_height_sensor"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
        )
        
        # Register callback
        self._update_callback = self._handle_coordinator_update
        coordinator.register_callback(self._update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callback."""
        self.coordinator.remove_callback(self._update_callback)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        """Return current height."""
        if not self.coordinator.is_connected:
            return None
        return round(self.coordinator.current_height_cm, 1)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.is_connected


class FLHDeskConnectionSensor(CoordinatorEntity[FLHDeskCoordinator], SensorEntity):
    """Sensor for Bluetooth connection status."""

    _attr_has_entity_name = True
    _attr_name = "Connection"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: FLHDeskCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{entry.unique_id}_connection"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
        )
        
        # Register callback
        self._update_callback = self._handle_coordinator_update
        coordinator.register_callback(self._update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callback."""
        self.coordinator.remove_callback(self._update_callback)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        """Return connection status."""
        return "Connected" if self.coordinator.is_connected else "Disconnected"

    @property
    def available(self) -> bool:
        """Return True (this sensor is always available)."""
        return True
