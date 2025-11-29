# Pulsar X3 Linux Control

Control your Pulsar X3 gaming mouse on Linux without needing the Windows Pulsar Fusion app. Works with both wired and wireless modes.

> **Disclaimer**: This is an unofficial, community-developed tool. It is not affiliated with, endorsed by, or supported by Pulsar Gaming Gears. Use at your own risk.

## Features

| Feature | Read | Write | Notes |
|---------|------|-------|-------|
| Firmware Version | ✅ | - | Mouse and dongle versions |
| DPI | ✅ | ✅ | 50-26000 DPI |
| DPI Stage | ✅ | ✅ | Switch between stages 1-6 |
| Battery | ✅ | - | Real-time percentage |
| Motion Sync | ✅ | ✅ | On/Off |
| Lift-off Distance | ✅ | ✅ | 0.7mm, 1mm, 2mm |
| Angle Snapping | ✅ | ✅ | On/Off |
| Ripple Control | ✅ | ✅ | On/Off |
| Debounce | ✅ | ✅ | Time in ms |
| Polling Rate | ⚠️ | ❌ | Read unreliable, write not working |

## Requirements

- Python 3.6+
- PyUSB library

## Installation

```bash
# Install PyUSB
pip install pyusb

# Setup udev rules for non-root access
sudo tee /etc/udev/rules.d/99-pulsar-mouse.rules << 'EOF'
SUBSYSTEM=="usb", ATTRS{idVendor}=="3710", ATTRS{idProduct}=="3410", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="3710", ATTRS{idProduct}=="5403", MODE="0666"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger

# Reconnect mouse after adding rules
```

## Usage

```bash
# Show all info
python3 pulsar_x3.py --info

# Set DPI directly
python3 pulsar_x3.py --dpi 800

# Switch DPI stage (like pressing the button on mouse)
python3 pulsar_x3.py --stage 2

# Check battery
python3 pulsar_x3.py --battery

# Motion sync
python3 pulsar_x3.py --motion-sync on
python3 pulsar_x3.py --motion-sync off

# Lift-off distance
python3 pulsar_x3.py --lod 0.7
python3 pulsar_x3.py --lod 1
python3 pulsar_x3.py --lod 2

# Angle snapping
python3 pulsar_x3.py --angle-snap on
python3 pulsar_x3.py --angle-snap off

# Ripple control
python3 pulsar_x3.py --ripple-control on
python3 pulsar_x3.py --ripple-control off

# Debounce time
python3 pulsar_x3.py --debounce 3
```

## Example Output

```
$ python3 pulsar_x3.py --info
✓ Found: Pulsar X3 (wireless mode)
======================================================================
Pulsar X3 Mouse Information
======================================================================

Dongle Firmware: 0123
Mouse Firmware: 00.00.10.16

DPI: 1600 (stage 3)
Motion Sync: OFF
Lift-off Distance: 1mm
Angle Snapping: OFF
Ripple Control: OFF
Debounce: 3ms
Battery: 80%
Polling Rate: 1000Hz (unreliable)
======================================================================
```

## Device Information

- **Vendor ID**: `0x3710` (Pulsar)
- **Product ID (Wired)**: `0x3410`
- **Product ID (Wireless)**: `0x5403`
- **Interface**: 3 (HID Feature Reports)

## Troubleshooting

### Permission denied
Make sure udev rules are installed and you've reconnected the mouse.

### Device not found
```bash
lsusb | grep 3710
```

### Polling rate
Polling rate read/write is not working correctly. Use the Windows Pulsar Fusion app to change polling rate.

### Settings reset after opening Windows Pulsar Fusion
It appears the Pulsar Fusion app syncs its saved data to the mouse on launch, overwriting any changes made on Linux.
