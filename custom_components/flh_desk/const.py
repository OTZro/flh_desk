"""Constants for the FLH Desk integration."""
from typing import Final

DOMAIN: Final = "flh_desk"

# Bluetooth UUIDs
SERVICE_UUID: Final = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
CHAR_RX_UUID: Final = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # Write to desk
CHAR_TX_UUID: Final = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Read from desk
DESCRIPTOR_UUID: Final = "00002902-0000-1000-8000-00805f9b34fb"

# Device info
MANUFACTURER: Final = "FLH"
MODEL: Final = "Height Adjustable Desk"

# Height limits (in cm)
DEFAULT_MIN_HEIGHT: Final = 72
DEFAULT_MAX_HEIGHT: Final = 122

# Command byte arrays
CMD_UP: Final = bytes([65, 32, 0, 0])
CMD_DOWN: Final = bytes([66, 32, 0, 0])
CMD_STOP: Final = bytes([64, 32, 0, 0])
CMD_INIT: Final = bytes([221, 1, 0, 0, 0, 0, 0, 0])
CMD_AUTO_MOVE_BASE: Final = bytes([64, 40])
CMD_AUTO_STOP: Final = bytes([195, 0, 0, 0])

# Memory positions
CMD_MOVE_TO_M1: Final = bytes([64, 33])
CMD_MOVE_TO_M2: Final = bytes([64, 34])
CMD_MOVE_TO_M3: Final = bytes([64, 36])
CMD_MOVE_TO_M4: Final = bytes([64, 40])

CMD_SAVE_TO_M1: Final = bytes([64, 49])
CMD_SAVE_TO_M2: Final = bytes([64, 50])
CMD_SAVE_TO_M3: Final = bytes([64, 52])
CMD_SAVE_TO_M4: Final = bytes([64, 56])

# Configuration
CONF_SENSITIVITY: Final = "sensitivity"
DEFAULT_SENSITIVITY: Final = 0

# Update interval
UPDATE_INTERVAL: Final = 1  # seconds
