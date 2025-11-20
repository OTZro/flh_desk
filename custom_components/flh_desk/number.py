"""Number platform for FLH Desk."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
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
    """Set up FLH Desk number platform."""
    coordinator: FLHDeskCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([
        FLHDeskHeightNumber(coordinator, entry),
        FLHDeskSensitivityNumber(coordinator, entry),
    ])


class FLHDeskHeightNumber(CoordinatorEntity[FLHDeskCoordinator], NumberEntity):
    """Number entity for precise height control."""

    _attr_has_entity_name = True
    _attr_name = "Target height"
    _attr_mode = NumberMode.BOX
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS

    def __init__(
        self,
        coordinator: FLHDeskCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{entry.unique_id}_height"
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
    def native_min_value(self) -> float:
        """Return minimum height."""
        return self.coordinator.min_height_cm

    @property
    def native_max_value(self) -> float:
        """Return maximum height."""
        return self.coordinator.max_height_cm

    @property
    def native_value(self) -> float | None:
        """Return current height."""
        if not self.coordinator.is_connected:
            return None
        return self.coordinator.current_height_cm

    @property
    def available(self) -> bool:
        """Return True to allow triggering connection."""
        return True

    async def async_set_native_value(self, value: float) -> None:
        """Set target height."""
        _LOGGER.debug("Setting target height to %.1f cm", value)
        await self.coordinator.async_move_to_height(value)


class FLHDeskSensitivityNumber(CoordinatorEntity[FLHDeskCoordinator], NumberEntity):
    """Number entity for sensitivity control."""

    _attr_has_entity_name = True
    _attr_name = "Sensitivity"
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0
    _attr_native_max_value = 8
    _attr_native_step = 1
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: FLHDeskCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensitivity number entity."""
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{entry.unique_id}_sensitivity"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
        )

    @property
    def native_value(self) -> float:
        """Return current sensitivity."""
        return float(self.coordinator._sensitivity)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.is_connected

    async def async_set_native_value(self, value: float) -> None:
        """Set sensitivity."""
        _LOGGER.debug("Setting sensitivity to %d", int(value))
        self.coordinator.set_sensitivity(int(value))
        self.async_write_ha_state()
