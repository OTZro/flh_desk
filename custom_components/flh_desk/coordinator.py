"""BLE Coordinator for FLH Desk."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from bleak import BleakClient, BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CHAR_RX_UUID,
    CHAR_TX_UUID,
    CMD_AUTO_MOVE_BASE,
    CMD_AUTO_STOP,
    CMD_DOWN,
    CMD_INIT,
    CMD_STOP,
    CMD_UP,
    DEFAULT_MAX_HEIGHT,
    DEFAULT_MIN_HEIGHT,
    DEFAULT_SENSITIVITY,
    DOMAIN,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# Common prefix for all commands (from APK: commonByteArray = {-35, 0})
COMMON_PREFIX = bytes([0xDD, 0x00])


def calculate_checksum(data: bytes) -> int:
    """Calculate checksum (sum of all bytes & 0x7F)."""
    return sum(data) & 0x7F


def build_command(
    command_bytes: bytes, 
    has_max_limit: bool = False, 
    has_min_limit: bool = False
) -> bytes:
    """Build complete command with prefix, limit flags, and checksum.
    
    Format: COMMON_PREFIX + modified_command_bytes + checksum
    
    The first byte of command_bytes is modified based on limit settings:
    - Both limits: first_byte + 0x30 (48)
    - Max only: first_byte + 0x10 (16)
    - Min only: first_byte + 0x20 (32)
    - No limits: first_byte (unchanged)
    """
    # Convert to mutable list
    cmd_list = list(command_bytes)
    
    # Modify first byte based on limit flags (APK's setFirstByteWithMaxMinLimit)
    if len(cmd_list) > 0:
        if has_max_limit and has_min_limit:
            cmd_list[0] = (cmd_list[0] + 0x30) & 0xFF
        elif has_max_limit:
            cmd_list[0] = (cmd_list[0] + 0x10) & 0xFF
        elif has_min_limit:
            cmd_list[0] = (cmd_list[0] + 0x20) & 0xFF
        # else: no modification needed
    
    modified_bytes = bytes(cmd_list)
    
    # Calculate checksum of modified command
    checksum = calculate_checksum(modified_bytes)
    
    # Build: DD 00 + modified_command + checksum
    return COMMON_PREFIX + modified_bytes + bytes([checksum])




class FLHDeskCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage FLH Desk BLE connection and data."""

    def __init__(self, hass: HomeAssistant, ble_device: BLEDevice) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{ble_device.address}",
            update_interval=None,  # We update on notifications
        )
        
        self.ble_device = ble_device
        self.client: BleakClient | None = None
        self._disconnect_lock = asyncio.Lock()
        self._is_connected = False

        # Reconnection settings
        self._reconnect_task: asyncio.Task | None = None
        self._should_reconnect = True
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 5  # seconds

        # Desk state
        self._current_height_mm: int = 0
        self._min_height_mm: int = DEFAULT_MIN_HEIGHT * 10
        self._max_height_mm: int = DEFAULT_MAX_HEIGHT * 10
        self._is_moving: bool = False
        self._sensitivity: int = DEFAULT_SENSITIVITY

        # Callbacks for real-time updates
        self._update_callbacks: list[Callable[[], None]] = []

    @property
    def current_height_cm(self) -> float:
        """Get current height in cm."""
        return self._current_height_mm / 10.0

    @property
    def min_height_cm(self) -> float:
        """Get minimum height in cm."""
        return self._min_height_mm / 10.0

    @property
    def max_height_cm(self) -> float:
        """Get maximum height in cm."""
        return self._max_height_mm / 10.0

    @property
    def is_moving(self) -> bool:
        """Return if desk is currently moving."""
        return self._is_moving

    @property
    def is_connected(self) -> bool:
        """Return connection status."""
        return self._is_connected

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback for state updates."""
        self._update_callbacks.append(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove a callback."""
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)

    @callback
    def _trigger_callbacks(self) -> None:
        """Trigger all registered callbacks."""
        for callback in self._update_callbacks:
            callback()

    async def async_connect(self) -> None:
        """Connect to the desk."""
        _LOGGER.debug("🔌 Connecting to %s", self.ble_device.address)
        
        self.client = await establish_connection(
            BleakClient,
            self.ble_device,
            self.ble_device.address,
            disconnected_callback=self._on_disconnect,
        )
        
        _LOGGER.debug("✅ BLE connection established")
        
        # Subscribe to notifications
        _LOGGER.debug("📡 Subscribing to notifications on %s", CHAR_TX_UUID)
        await self.client.start_notify(
            CHAR_TX_UUID,
            self._notification_handler,
        )
        _LOGGER.debug("✅ Notification subscription successful")
        
        self._is_connected = True
        _LOGGER.info("Connected to FLH Desk at %s", self.ble_device.address)
        
        # 1. Send STOP command to wake up / handshake (Mimic APK behavior)
        _LOGGER.debug("🚀 Sending STOP command (Wake Up)...")
        await self.async_stop()
        
        # 2. Wait for potential response (APK does this)
        _LOGGER.debug("⏱️  Waiting 1.0s for Wake Up response...")
        await asyncio.sleep(1.0)
        
        # 3. Initialize desk - INIT command already has DD prefix, send it raw
        _LOGGER.debug("🚀 Sending INIT command: %s", CMD_INIT.hex())
        await self._send_command(CMD_INIT)
        _LOGGER.debug("⏱️  Waiting 500ms for INIT response...")
        await asyncio.sleep(0.5)  # Wait for init response

    async def async_disconnect(self) -> None:
        """Disconnect from the desk."""
        async with self._disconnect_lock:
            if self.client and self.client.is_connected:
                _LOGGER.debug("Disconnecting from %s", self.ble_device.address)
                await self.client.disconnect()
            self._is_connected = False

    def _on_disconnect(self, _client: BleakClient) -> None:
        """Handle disconnection."""
        _LOGGER.warning("Disconnected from FLH Desk")
        self._is_connected = False
        self._trigger_callbacks()

        # Start reconnection task if enabled
        if self._should_reconnect and self._reconnect_task is None:
            self._reconnect_task = self.hass.async_create_task(
                self._async_reconnect()
            )

    async def _async_reconnect(self) -> None:
        """Attempt to reconnect to the desk."""
        attempt = 0

        while self._should_reconnect and attempt < self._max_reconnect_attempts:
            attempt += 1
            _LOGGER.info(
                "🔄 Reconnection attempt %d/%d in %d seconds...",
                attempt,
                self._max_reconnect_attempts,
                self._reconnect_delay,
            )

            await asyncio.sleep(self._reconnect_delay)

            if not self._should_reconnect:
                break

            try:
                # Update BLE device reference (it may have changed)
                from homeassistant.components import bluetooth
                ble_device = bluetooth.async_ble_device_from_address(
                    self.hass, self.ble_device.address, connectable=True
                )
                if ble_device:
                    self.ble_device = ble_device

                await self.async_connect()
                _LOGGER.info("✅ Reconnected to FLH Desk successfully")
                self._reconnect_task = None
                return

            except Exception as err:
                _LOGGER.warning(
                    "❌ Reconnection attempt %d failed: %s",
                    attempt,
                    err,
                )

        if self._should_reconnect:
            _LOGGER.error(
                "🚫 Failed to reconnect after %d attempts",
                self._max_reconnect_attempts,
            )

        self._reconnect_task = None

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and stop reconnection."""
        _LOGGER.debug("Shutting down coordinator")
        self._should_reconnect = False

        # Cancel reconnection task if running
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None

        await self.async_disconnect()

    def _notification_handler(
        self, _characteristic: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        """Handle incoming notifications from desk."""
        # Log RAW data first - before any filtering
        _LOGGER.debug("📩 RAW notification received: %s (length=%d bytes)", 
                     data.hex() if data else "<empty>", len(data))
        
        if not data or len(data) == 0:
            _LOGGER.warning("⚠️  Received EMPTY notification")
            return
        
        # Log each byte for detailed analysis
        _LOGGER.debug("📊 Bytes breakdown: %s", [f"{b:02X}({b})" for b in data])
        
        # Data must be at least 11 bytes and start with 0x9D
        if len(data) < 11 or data[0] != 0x9D:
            _LOGGER.warning(
                "⚠️  Invalid format - len=%d, first_byte=0x%02X (expected: len>=11, first=0x9D)",
                len(data), 
                data[0] if len(data) > 0 else 0
            )
            return
        
        cmd_type = data[1]
        _LOGGER.debug("📋 Command type: 0x%02X", cmd_type)
        
        if cmd_type == 0x00:  # Init response
            _LOGGER.info("✅ Initialization response received")
            # Min/max limits are in bytes 6-9 (12-bit big-endian format)
            # Formula: (B2 & 0xFF) | ((B1 & 0x0F) << 8)
            min_b1, min_b2 = data[6], data[7]
            max_b1, max_b2 = data[8], data[9]
            self._min_height_mm = (min_b2 & 0xFF) | ((min_b1 & 0x0F) << 8)
            self._max_height_mm = (max_b2 & 0xFF) | ((max_b1 & 0x0F) << 8)
            _LOGGER.info(
                "📏 Height limits: %.1f - %.1f cm (min bytes: %02X %02X, max bytes: %02X %02X)",
                self.min_height_cm,
                self.max_height_cm,
                min_b1, min_b2, max_b1, max_b2,
            )
            
        elif cmd_type == 0x01:  # Height update
            # Current height is in bytes 6-7 (12-bit big-endian format from APK)
            # B1's low 4 bits are high byte, B2 is low byte
            # Formula: (B2 & 0xFF) | ((B1 & 0x0F) << 8)
            b1 = data[6]
            b2 = data[7]
            self._current_height_mm = (b2 & 0xFF) | ((b1 & 0x0F) << 8)
            _LOGGER.debug("📏 Current height: %.1f cm (raw: %d mm, bytes: %02X %02X)",
                         self.current_height_cm, self._current_height_mm, b1, b2)
            
            # Check if moving (need to analyze more data bytes)
            # For now, assume moving if receiving updates
            # self._is_moving = bool(data[4] & 0x01)
        
        # Trigger callbacks for real-time UI updates
        self._trigger_callbacks()
        
        # Update coordinator data
        self.async_set_updated_data({
            "height_cm": self.current_height_cm,
            "min_height_cm": self.min_height_cm,
            "max_height_cm": self.max_height_cm,
            "is_moving": self.is_moving,
            "is_connected": self.is_connected,
        })

    async def _send_command(self, command: bytes) -> None:
        """Send a command to the desk."""
        if not self.client or not self.client.is_connected:
            raise UpdateFailed("Not connected to desk")
        
        _LOGGER.debug("📤 Sending command: %s (%d bytes)", command.hex(), len(command))
        _LOGGER.debug("📊 Command bytes: %s", [f"{b:02X}({b})" for b in command])
        
        try:
            await self.client.write_gatt_char(CHAR_RX_UUID, command, response=False)
            _LOGGER.debug("✅ Command sent successfully")
        except Exception as err:
            _LOGGER.error("❌ Failed to send command: %s", err, exc_info=True)
            raise UpdateFailed(f"Failed to send command: {err}") from err

    async def async_move_up(self) -> None:
        """Move desk up."""
        _LOGGER.debug("Moving desk up")
        # Build: UP command + sensitivity
        command_bytes = bytes(list(CMD_UP) + [self._sensitivity])
        full_command = build_command(command_bytes)
        await self._send_command(full_command)

    async def async_move_down(self) -> None:
        """Move desk down."""
        _LOGGER.debug("Moving desk down")
        # Build: DOWN command + sensitivity
        command_bytes = bytes(list(CMD_DOWN) + [self._sensitivity])
        full_command = build_command(command_bytes)
        await self._send_command(full_command)

    async def async_stop(self) -> None:
        """Stop desk movement."""
        _LOGGER.debug("Stopping desk")
        # Build: STOP command + sensitivity
        command_bytes = bytes(list(CMD_STOP) + [self._sensitivity])
        full_command = build_command(command_bytes)
        await self._send_command(full_command)

    async def async_move_to_height(self, height_cm: float) -> None:
        """Move desk to specific height."""
        height_mm = int(height_cm * 10)

        # Clamp to limits
        height_mm = max(self._min_height_mm, min(height_mm, self._max_height_mm))

        _LOGGER.debug("Moving to %.1f cm (%d mm)", height_mm / 10, height_mm)

        # Build auto-move command
        # Format: [64, 40] + height_high + height_low + sensitivity (big-endian from APK)
        height_high = (height_mm >> 8) & 0xFF
        height_low = height_mm & 0xFF

        command_bytes = bytes(
            list(CMD_AUTO_MOVE_BASE) + [height_high, height_low, self._sensitivity]
        )
        full_command = build_command(command_bytes)

        await self._send_command(full_command)

    async def async_stop_auto_move(self) -> None:
        """Stop automatic movement."""
        _LOGGER.debug("Stopping auto-move")
        # Build: AUTO_STOP command
        full_command = build_command(CMD_AUTO_STOP)
        await self._send_command(full_command)

    def set_sensitivity(self, sensitivity: int) -> None:
        """Set movement sensitivity (0-8)."""
        self._sensitivity = max(0, min(8, sensitivity))
        _LOGGER.debug("Sensitivity set to %d", self._sensitivity)
