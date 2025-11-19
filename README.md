# FLH Desk Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/your-username/ha-flh-desk.svg)](https://github.com/your-username/ha-flh-desk/releases)

Control your FLH height-adjustable desk directly from Home Assistant via Bluetooth LE.

## Features

- 🎚️ **Cover Entity**: Control desk height with open/close/stop/position commands
- 🎯 **Number Entity**: Set precise target height in centimeters
- 📊 **Sensors**: Monitor current height and connection status
- ⚙️ **Sensitivity Control**: Adjust movement speed (0-8)
- 🔍 **Auto-Discovery**: Automatically finds FLH desks via Bluetooth
- 📱 **Native Integration**: Uses Home Assistant's built-in Bluetooth framework

## Requirements

- Home Assistant 2022.9.0 or newer
- Bluetooth adapter (built-in or USB dongle)
- FLH height-adjustable desk with Bluetooth support

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add `https://github.com/your-username/ha-flh-desk` as repository
6. Select "Integration" as category
7. Click "Add"
8. Search for "FLH Desk" and click "Download"
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/flh_desk` directory to your Home Assistant's `custom_components` folder
2. Restart Home Assistant

## Configuration

### Via UI (Recommended)

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "FLH Desk"
4. Follow the configuration steps:
   - The integration will automatically discover nearby FLH desks
   - Select your desk from the list
   - Click **Submit**

### Via Auto-Discovery

If Bluetooth is enabled, Home Assistant will automatically discover your FLH desk and show a notification to set it up.

## Entities

After setup, the following entities will be created:

### Cover

- **`cover.flh_desk`**: Main desk control
  - **Open**: Move to maximum height
  - **Close**: Move to minimum height
  - **Stop**: Stop movement
  - **Set Position**: Move to specific position (0-100%)

### Numbers

- **`number.flh_desk_target_height`**: Set precise height in cm (72-122cm)
- **`number.flh_desk_sensitivity`**: Adjust movement sensitivity (0-8)

### Sensors

- **`sensor.flh_desk_height`**: Current desk height in cm
- **`sensor.flh_desk_connection`**: Bluetooth connection status

## Usage Examples

### Basic Automations

#### Wake Up - Raise Desk
```yaml
automation:
  - alias: "Morning Desk Raise"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - service: cover.set_cover_position
        target:
          entity_id: cover.flh_desk
        data:
          position: 100  # Fully raised
```

#### Lunch Break - Lower Desk
```yaml
automation:
  - alias: "Lunch Break Lower Desk"
    trigger:
      - platform: time
        at: "12:00:00"
    action:
      - service: number.set_value
        target:
          entity_id: number.flh_desk_target_height
        data:
          value: 75  # 75cm sitting height
```

#### Precise Height Control
```yaml
script:
  desk_standing_position:
    sequence:
      - service: number.set_value
        target:
          entity_id: number.flh_desk_target_height
        data:
          value: 110  # 110cm standing height
```

### Dashboard Card

```yaml
type: entities
title: FLH Desk
entities:
  - entity: cover.flh_desk
  - entity: number.flh_desk_target_height
  - entity: sensor.flh_desk_height
  - entity: number.flh_desk_sensitivity
    name: Movement Speed
  - entity: sensor.flh_desk_connection
```

### Voice Control (with Alexa/Google Assistant)

Once configured, you can control your desk with voice commands:
- "Alexa, open the desk" (move to max height)
- "Alexa, close the desk" (move to min height)
- "Alexa, set desk to 50 percent" (move to 50% position)

## Troubleshooting

### Desk Not Discovered

- Ensure the desk is powered on
- Check that Bluetooth is enabled in Home Assistant
- Verify your Bluetooth adapter is working: **Settings** → **System** → **Hardware**
- Try restarting Home Assistant

### Connection Issues

- Move the Bluetooth adapter closer to the desk
- Check for Bluetooth interference from other devices
- Restart the integration: **Settings** → **Devices & Services** → **FLH Desk** → **⋮** → **Reload**

### Desk Not Responding

- Check the connection sensor: `sensor.flh_desk_connection`
- Try reducing the sensitivity if movements are jerky
- Remove and re-add the integration

## Technical Details

### Bluetooth Protocol

This integration uses the following Bluetooth LE characteristics:
- **Service UUID**: `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`
- **RX UUID** (Write): `6E400002-B5A3-F393-E0A9-E50E24DCCA9E`
- **TX UUID** (Notify): `6E400003-B5A3-F393-E0A9-E50E24DCCA9E`

### Height Encoding

- Height is transmitted as 2 bytes (little-endian) in millimeters
- Range: 720mm (72cm) to 1220mm (122cm)
- Precision: 0.1mm

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This is an unofficial integration and is not affiliated with or endorsed by FLH or the desk manufacturer.

## Credits

- Protocol analysis based on reverse engineering of the MySmartPal Android application
- Built using Home Assistant's official Bluetooth integration framework