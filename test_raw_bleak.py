import asyncio
import logging
import sys
from bleak import BleakClient, BleakScanner

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# UUIDs
SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
CHAR_RX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # Write
CHAR_TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Notify

# Commands
CMD_STOP = bytes.fromhex("dd00402000000060")
CMD_INIT = bytes.fromhex("dd01000000000000")

def notification_handler(sender, data):
    """Handle incoming notifications."""
    logger.info(f"📩 Notification from {sender}: {data.hex()} (len={len(data)})")
    if len(data) > 0:
        logger.info(f"   Bytes: {[hex(b) for b in data]}")

async def run():
    logger.info("🔍 Scanning for FLH Desk...")
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and "FLH" in d.name
    )
    
    if not device:
        logger.error("❌ Desk not found")
        return

    logger.info(f"✅ Found desk: {device.name} ({device.address})")

    async with BleakClient(device) as client:
        logger.info(f"🔌 Connected: {client.is_connected}")
        
        # List services
        for service in client.services:
            logger.info(f"📦 Service: {service.uuid}")
            for char in service.characteristics:
                logger.info(f"   📝 Char: {char.uuid} | Props: {char.properties}")

        # Subscribe
        logger.info("📡 Subscribing to notifications...")
        await client.start_notify(CHAR_TX_UUID, notification_handler)
        
        # Wake Up Sequence
        logger.info("🚀 Sending STOP (Wake Up)...")
        await client.write_gatt_char(CHAR_RX_UUID, CMD_STOP)
        
        logger.info("⏱️  Waiting 1.0s...")
        await asyncio.sleep(1.0)
        
        logger.info("🚀 Sending INIT...")
        await client.write_gatt_char(CHAR_RX_UUID, CMD_INIT)
        
        logger.info("⏱️  Waiting 5.0s for response...")
        await asyncio.sleep(5.0)
        
        logger.info("🔌 Disconnecting...")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"❌ Error: {e}")
