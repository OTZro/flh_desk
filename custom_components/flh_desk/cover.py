"""Cover platform for FLH Desk."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
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
    """Set up FLH Desk cover platform."""
    coordinator: FLHDeskCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([FLHDeskCover(coordinator, entry)])


class FLHDeskCover(CoordinatorEntity[FLHDeskCoordinator], CoverEntity):
    """Representation of FLH Desk as a cover entity."""

    _attr_device_class = CoverDeviceClass.DAMPER
    _attr_has_entity_name = True
    _attr_name = None  # Use device name

    def __init__(
        self,
        coordinator: FLHDeskCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the cover."""
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{entry.unique_id}_cover"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name="FLH Desk",
            manufacturer=MANUFACTURER,
            model=MODEL,
            connections={(
                "bluetooth",
                coordinator.ble_device.address,
            )},
        )
        
        # Register callback for real-time updates
        self._update_callback = self._handle_coordinator_update
        coordinator.register_callback(self._update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callback when entity is removed."""
        self.coordinator.remove_callback(self._update_callback)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator."""
        self.async_write_ha_state()

    @property
    def supported_features(self) -> CoverEntityFeature:
        """Flag supported features."""
        return (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )

    @property
    def current_cover_position(self) -> int | None:
        """Return current position (0-100)."""
        if not self.coordinator.is_connected:
            return None
        
        # Convert height to percentage
        height_range = self.coordinator.max_height_cm - self.coordinator.min_height_cm
        if height_range == 0:
            return 0
        
        position = (
            (self.coordinator.current_height_cm - self.coordinator.min_height_cm)
            / height_range
            * 100
        )
        return int(max(0, min(100, position)))

    @property
    def is_opening(self) -> bool:
        """Return if cover is opening."""
        return self.coordinator.is_moving and self.current_cover_position is not None

    @property
    def is_closing(self) -> bool:
        """Return if cover is closing."""
        return self.coordinator.is_moving and self.current_cover_position is not None

    @property
    def is_closed(self) -> bool | None:
        """Return if cover is closed."""
        if self.current_cover_position is None:
            return None
        return self.current_cover_position == 0

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.is_connected

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover (move to max height)."""
        _LOGGER.debug("Opening cover (moving to max height)")
        await self.coordinator.async_move_to_height(self.coordinator.max_height_cm)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover (move to min height)."""
        _LOGGER.debug("Closing cover (moving to min height)")
        await self.coordinator.async_move_to_height(self.coordinator.min_height_cm)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        _LOGGER.debug("Stopping cover")
        await self.coordinator.async_stop()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move cover to a specific position (0-100)."""
        position = kwargs.get("position", 0)
        
        # Convert percentage to height
        height_range = self.coordinator.max_height_cm - self.coordinator.min_height_cm
        target_height = self.coordinator.min_height_cm + (position / 100 * height_range)
        
        _LOGGER.debug("Setting cover position to %d%% (%.1f cm)", position, target_height)
        await self.coordinator.async_move_to_height(target_height)
