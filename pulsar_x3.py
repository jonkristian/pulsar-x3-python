#!/usr/bin/env python3
"""
Pulsar X3 Mouse Control for Linux
Works with both wired (USB cable) and wireless (dongle) modes

Usage:
    python3 pulsar_x3.py --info
    python3 pulsar_x3.py --dpi 800
    python3 pulsar_x3.py --stage 2
    python3 pulsar_x3.py --motion-sync on
    python3 pulsar_x3.py --lod 1
    python3 pulsar_x3.py --angle-snap off
    python3 pulsar_x3.py --ripple-control on
    python3 pulsar_x3.py --debounce 3
"""

import usb.core
import struct
import sys
import argparse
import time

VID = 0x3710
PID_WIRED = 0x3410
PID_WIRELESS = 0x5403

def calculate_checksum(data):
    """Calculate 16-bit checksum"""
    return sum(data[:-2]) & 0xFFFF

def send_command(dev, command_bytes):
    """Send command and return response"""
    packet = bytearray(64)
    packet[0] = 0x00  # Report ID
    for i, byte in enumerate(command_bytes):
        packet[i+1] = byte

    checksum = calculate_checksum(packet)
    struct.pack_into('<H', packet, 62, checksum)

    dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)
    time.sleep(0.05)

    response = dev.ctrl_transfer(0xA1, 0x01, 0x0300, 3, 64, timeout=1000)
    return response

def set_dpi(dev, dpi):
    """Set mouse DPI"""
    print(f"Setting DPI to {dpi}...")

    packet = bytearray(64)
    packet[0:7] = [0x00, 0x05, 0x02, 0x05, 0x00, 0x00, 0x01]
    struct.pack_into('<H', packet, 7, dpi)
    struct.pack_into('<H', packet, 9, dpi)
    checksum = calculate_checksum(packet)
    struct.pack_into('<H', packet, 62, checksum)

    dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)
    print(f"✓ DPI set to {dpi}")
    print("Move your mouse to feel the difference!")

def set_stage(dev, stage):
    """Switch DPI stage (1-6)"""
    if not 1 <= stage <= 6:
        print("ERROR: Stage must be between 1 and 6")
        return False

    print(f"Switching to DPI stage {stage}...")

    # Command: 05 01 02 00 00 01 XX (from capture)
    packet = bytearray(64)
    packet[0:8] = [0x00, 0x05, 0x01, 0x02, 0x00, 0x00, 0x01, stage]
    checksum = calculate_checksum(packet)
    struct.pack_into('<H', packet, 62, checksum)

    dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)
    print(f"✓ Switched to DPI stage {stage}")
    return True


def query_version(dev):
    """Query mouse firmware version"""
    response = send_command(dev, [0x01, 0x87, 0x04])
    # Bytes 6-7 contain version, displayed as hex
    minor = response[6]
    major = response[7]
    return f"00.00.{major:02x}.{minor:02x}"

def query_info(dev):
    """Query mouse information"""
    print("="*70)
    print("Pulsar X3 Mouse Information")
    print("="*70)

    # Dongle version from USB descriptor
    dongle_version = f"{dev.bcdDevice:04x}"
    print(f"\nDongle Firmware: {dongle_version}")

    # Mouse version from query
    mouse_version = query_version(dev)
    print(f"Mouse Firmware: {mouse_version}")

    # Query DPI and stage
    dpi_x, dpi_y, stage = query_dpi(dev)
    if dpi_x == dpi_y:
        print(f"\nDPI: {dpi_x} (stage {stage})")
    else:
        print(f"\nDPI: {dpi_x} x {dpi_y} (stage {stage})")

    # Motion Sync
    motion_status, _ = query_motion_sync(dev)
    print(f"Motion Sync: {motion_status}")

    # LOD
    lod_str, _ = query_lod(dev)
    print(f"Lift-off Distance: {lod_str}")

    # Angle snapping
    angle_status, _ = query_angle_snap(dev)
    print(f"Angle Snapping: {angle_status}")

    # Ripple Control
    ripple_status, _ = query_ripple_control(dev)
    print(f"Ripple Control: {ripple_status}")

    # Debounce
    debounce = query_debounce(dev)
    print(f"Debounce: {debounce}ms")

    # Battery
    response = send_command(dev, [0x08, 0x81, 0x01])
    battery = response[6]
    print(f"Battery: {battery}%")

    # Polling rate query (unreliable - may not reflect actual rate)
    poll_rate, poll_value = query_polling_rate(dev)
    if poll_rate:
        print(f"Polling Rate: {poll_rate}Hz (unreliable)")
    else:
        print(f"Polling Rate: Unknown ({poll_value})")

    print("="*70)

def query_battery(dev):
    """Query battery percentage"""
    # Battery is in response to command 08 81 01, byte 6
    response = send_command(dev, [0x08, 0x81, 0x01])
    battery_percent = response[6]

    print(f"\n🔋 Battery: {battery_percent}%")

def set_motion_sync(dev, enable):
    """Enable or disable motion sync"""
    value = 0x01 if enable else 0x00
    state = "ON" if enable else "OFF"
    print(f"Setting Motion Sync {state}...")

    # Command: 07 05 02 00 00 01 XX (from capture)
    packet = bytearray(64)
    packet[0:8] = [0x00, 0x07, 0x05, 0x02, 0x00, 0x00, 0x01, value]
    checksum = calculate_checksum(packet)
    struct.pack_into('<H', packet, 62, checksum)

    dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)
    print(f"✓ Motion Sync {state}")

def query_motion_sync(dev):
    """Query motion sync status"""
    response = send_command(dev, [0x07, 0x85, 0x02])
    value = response[7]
    status = "ON" if value == 1 else "OFF"
    return status, value

def query_lod(dev):
    """Query LOD (lift-off distance)"""
    response = send_command(dev, [0x07, 0x82, 0x03])
    value = response[8]
    # LOD is stored as mm * 10 (7=0.7mm, 10=1mm, 20=2mm)
    lod_map = {7: "0.7mm", 10: "1mm", 20: "2mm"}
    lod_str = lod_map.get(value, f"{value/10}mm")
    return lod_str, value

def set_lod(dev, lod_mm):
    """Set LOD (lift-off distance). Options: 0.7, 1, 2 (in mm)"""
    # Convert mm to value (mm * 10)
    lod_value = int(lod_mm * 10)
    valid_values = {7: "0.7mm", 10: "1mm", 20: "2mm"}

    if lod_value not in valid_values:
        print(f"ERROR: LOD must be 0.7, 1, or 2 (mm)")
        return False

    print(f"Setting LOD to {valid_values[lod_value]}...")

    # Command: 07 02 03 00 00 01 02 XX (from capture, XX = mm*10)
    packet = bytearray(64)
    packet[0:9] = [0x00, 0x07, 0x02, 0x03, 0x00, 0x00, 0x01, 0x02, lod_value]
    checksum = calculate_checksum(packet)
    struct.pack_into('<H', packet, 62, checksum)

    dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)
    print(f"✓ LOD set to {valid_values[lod_value]}")
    return True

def query_angle_snap(dev):
    """Query angle snapping status"""
    response = send_command(dev, [0x07, 0x84, 0x02])
    value = response[7]
    status = "ON" if value == 1 else "OFF"
    return status, value

def query_ripple_control(dev):
    """Query ripple control status"""
    response = send_command(dev, [0x07, 0x83, 0x02])
    value = response[7]
    status = "ON" if value == 1 else "OFF"
    return status, value

def set_ripple_control(dev, enable):
    """Enable or disable ripple control"""
    value = 0x01 if enable else 0x00
    state = "ON" if enable else "OFF"
    print(f"Setting Ripple Control {state}...")

    # Command: 07 03 02 00 00 01 XX (from capture)
    packet = bytearray(64)
    packet[0:8] = [0x00, 0x07, 0x03, 0x02, 0x00, 0x00, 0x01, value]
    checksum = calculate_checksum(packet)
    struct.pack_into('<H', packet, 62, checksum)

    dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)
    print(f"✓ Ripple Control {state}")

def query_debounce(dev):
    """Query debounce time in ms"""
    response = send_command(dev, [0x04, 0x83, 0x03])
    value = response[7]
    return value

def set_debounce(dev, ms):
    """Set debounce time in ms"""
    print(f"Setting Debounce to {ms}ms...")

    # Command: 04 03 03 00 00 01 XX (from capture)
    packet = bytearray(64)
    packet[0:8] = [0x00, 0x04, 0x03, 0x03, 0x00, 0x00, 0x01, ms]
    checksum = calculate_checksum(packet)
    struct.pack_into('<H', packet, 62, checksum)

    dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)
    print(f"✓ Debounce set to {ms}ms")

def query_dpi(dev):
    """Query current DPI and stage"""
    # Query DPI values
    response = send_command(dev, [0x05, 0x82, 0x05])
    dpi_x = response[7] | (response[8] << 8)
    dpi_y = response[9] | (response[10] << 8)

    # Query current stage
    response = send_command(dev, [0x05, 0x81, 0x02])
    stage = response[7]

    return dpi_x, dpi_y, stage

def set_angle_snap(dev, enable):
    """Enable or disable angle snapping"""
    value = 0x01 if enable else 0x00
    state = "ON" if enable else "OFF"
    print(f"Setting Angle Snapping {state}...")

    # Command: 07 04 02 00 00 01 XX (from capture)
    packet = bytearray(64)
    packet[0:8] = [0x00, 0x07, 0x04, 0x02, 0x00, 0x00, 0x01, value]
    checksum = calculate_checksum(packet)
    struct.pack_into('<H', packet, 62, checksum)

    dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)
    print(f"✓ Angle Snapping {state}")

# Polling rate query value mapping (unreliable - doesn't reflect actual rate)
POLLING_QUERY_TO_RATE = {
    240: 125,
    120: 250,
    60: 500,
    30: 1000,
    15: 2000,
    8: 4000,
    4: 8000,
}

def query_polling_rate(dev):
    """Query current polling rate (unreliable)"""
    response = send_command(dev, [0x08, 0x85, 0x03])
    value = response[7]
    rate = POLLING_QUERY_TO_RATE.get(value, None)
    return rate, value


def main():
    parser = argparse.ArgumentParser(
        description='Control Pulsar X3 mouse (wired or wireless)')
    parser.add_argument('--dpi', type=int, help='Set DPI (50-26000)')
    parser.add_argument('--stage', type=int, choices=[1, 2, 3, 4, 5, 6], help='Switch DPI stage (1-6)')
    parser.add_argument('--battery', action='store_true', help='Show battery percentage')
    parser.add_argument('--info', action='store_true', help='Show device info')
    parser.add_argument('--motion-sync', choices=['on', 'off'], help='Enable/disable motion sync')
    parser.add_argument('--lod', type=float, choices=[0.7, 1, 2], help='Set lift-off distance (mm)')
    parser.add_argument('--angle-snap', choices=['on', 'off'], help='Enable/disable angle snapping')
    parser.add_argument('--ripple-control', choices=['on', 'off'], help='Enable/disable ripple control')
    parser.add_argument('--debounce', type=int, help='Set debounce time in ms')

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    # Find device - try wireless first, then wired
    dev = usb.core.find(idVendor=VID, idProduct=PID_WIRELESS)
    mode = "wireless"

    if not dev:
        dev = usb.core.find(idVendor=VID, idProduct=PID_WIRED)
        mode = "wired"

    if not dev:
        print("ERROR: Pulsar X3 mouse not found!")
        print("Make sure the mouse is connected (wired or wireless)")
        return 1

    print(f"✓ Found: Pulsar X3 ({mode} mode)")

    # Detach kernel driver
    if dev.is_kernel_driver_active(3):
        dev.detach_kernel_driver(3)

    try:
        # Execute command
        if args.dpi:
            if 50 <= args.dpi <= 26000:
                set_dpi(dev, args.dpi)
            else:
                print("ERROR: DPI must be between 50 and 26000")
                return 1
        elif args.stage:
            set_stage(dev, args.stage)
        elif args.battery:
            query_battery(dev)
        elif args.motion_sync:
            set_motion_sync(dev, args.motion_sync == 'on')
        elif args.lod:
            set_lod(dev, args.lod)
        elif args.angle_snap:
            set_angle_snap(dev, args.angle_snap == 'on')
        elif args.ripple_control:
            set_ripple_control(dev, args.ripple_control == 'on')
        elif args.debounce is not None:
            set_debounce(dev, args.debounce)
        elif args.info:
            query_info(dev)

    finally:
        try:
            dev.attach_kernel_driver(3)
        except:
            pass

    return 0

if __name__ == '__main__':
    sys.exit(main())
