#!/usr/bin/env python3
"""
Pulsar X3 Mouse Control - GTK4 GUI
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio

import usb.core
import struct
import time
import threading

VID = 0x3710
PID_WIRED = 0x3410
PID_WIRELESS = 0x5403


class PulsarDevice:
    """Handle communication with the Pulsar X3 mouse"""

    def __init__(self):
        self.dev = None
        self.mode = None

    def connect(self):
        """Find and connect to the mouse"""
        self.dev = usb.core.find(idVendor=VID, idProduct=PID_WIRELESS)
        self.mode = "wireless"

        if not self.dev:
            self.dev = usb.core.find(idVendor=VID, idProduct=PID_WIRED)
            self.mode = "wired"

        if not self.dev:
            return False

        if self.dev.is_kernel_driver_active(3):
            self.dev.detach_kernel_driver(3)

        return True

    def disconnect(self):
        """Reattach kernel driver"""
        if self.dev:
            try:
                self.dev.attach_kernel_driver(3)
            except:
                pass

    def send_command(self, command_bytes):
        """Send command and return response"""
        packet = bytearray(64)
        packet[0] = 0x00
        for i, byte in enumerate(command_bytes):
            packet[i+1] = byte

        checksum = sum(packet[:-2]) & 0xFFFF
        struct.pack_into('<H', packet, 62, checksum)

        self.dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)
        time.sleep(0.05)

        response = self.dev.ctrl_transfer(0xA1, 0x01, 0x0300, 3, 64, timeout=1000)
        return response

    def get_info(self):
        """Get all mouse info"""
        info = {}

        # Dongle firmware
        info['dongle_fw'] = f"{self.dev.bcdDevice:04x}"

        # Mouse firmware
        response = self.send_command([0x01, 0x87, 0x04])
        info['mouse_fw'] = f"00.00.{response[7]:02x}.{response[6]:02x}"

        # DPI and stage
        response = self.send_command([0x05, 0x82, 0x05])
        info['dpi'] = response[7] | (response[8] << 8)

        response = self.send_command([0x05, 0x81, 0x02])
        info['stage'] = response[7]

        # Motion sync
        response = self.send_command([0x07, 0x85, 0x02])
        info['motion_sync'] = response[7] == 1

        # LOD
        response = self.send_command([0x07, 0x82, 0x03])
        lod_value = response[8]
        lod_map = {7: 0.7, 10: 1.0, 20: 2.0}
        info['lod'] = lod_map.get(lod_value, 1.0)

        # Angle snap
        response = self.send_command([0x07, 0x84, 0x02])
        info['angle_snap'] = response[7] == 1

        # Ripple control
        response = self.send_command([0x07, 0x83, 0x02])
        info['ripple_control'] = response[7] == 1

        # Debounce
        response = self.send_command([0x04, 0x83, 0x03])
        info['debounce'] = response[7]

        # Battery
        response = self.send_command([0x08, 0x81, 0x01])
        info['battery'] = response[6]

        return info

    def set_dpi(self, dpi):
        """Set DPI value"""
        packet = bytearray(64)
        packet[0:7] = [0x00, 0x05, 0x02, 0x05, 0x00, 0x00, 0x01]
        struct.pack_into('<H', packet, 7, dpi)
        struct.pack_into('<H', packet, 9, dpi)
        checksum = sum(packet[:-2]) & 0xFFFF
        struct.pack_into('<H', packet, 62, checksum)
        self.dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)

    def set_stage(self, stage):
        """Set DPI stage (1-6)"""
        packet = bytearray(64)
        packet[0:8] = [0x00, 0x05, 0x01, 0x02, 0x00, 0x00, 0x01, stage]
        checksum = sum(packet[:-2]) & 0xFFFF
        struct.pack_into('<H', packet, 62, checksum)
        self.dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)

    def set_motion_sync(self, enable):
        """Enable/disable motion sync"""
        value = 0x01 if enable else 0x00
        packet = bytearray(64)
        packet[0:8] = [0x00, 0x07, 0x05, 0x02, 0x00, 0x00, 0x01, value]
        checksum = sum(packet[:-2]) & 0xFFFF
        struct.pack_into('<H', packet, 62, checksum)
        self.dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)

    def set_lod(self, lod_mm):
        """Set lift-off distance"""
        lod_value = int(lod_mm * 10)
        packet = bytearray(64)
        packet[0:9] = [0x00, 0x07, 0x02, 0x03, 0x00, 0x00, 0x01, 0x02, lod_value]
        checksum = sum(packet[:-2]) & 0xFFFF
        struct.pack_into('<H', packet, 62, checksum)
        self.dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)

    def set_angle_snap(self, enable):
        """Enable/disable angle snapping"""
        value = 0x01 if enable else 0x00
        packet = bytearray(64)
        packet[0:8] = [0x00, 0x07, 0x04, 0x02, 0x00, 0x00, 0x01, value]
        checksum = sum(packet[:-2]) & 0xFFFF
        struct.pack_into('<H', packet, 62, checksum)
        self.dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)

    def set_ripple_control(self, enable):
        """Enable/disable ripple control"""
        value = 0x01 if enable else 0x00
        packet = bytearray(64)
        packet[0:8] = [0x00, 0x07, 0x03, 0x02, 0x00, 0x00, 0x01, value]
        checksum = sum(packet[:-2]) & 0xFFFF
        struct.pack_into('<H', packet, 62, checksum)
        self.dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)

    def set_debounce(self, ms):
        """Set debounce time"""
        packet = bytearray(64)
        packet[0:8] = [0x00, 0x04, 0x03, 0x03, 0x00, 0x00, 0x01, ms]
        checksum = sum(packet[:-2]) & 0xFFFF
        struct.pack_into('<H', packet, 62, checksum)
        self.dev.ctrl_transfer(0x21, 0x09, 0x0300, 3, bytes(packet), timeout=1000)


class PulsarWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Pulsar X3 Control")
        self.set_default_size(380, 550)

        self.device = PulsarDevice()
        self.updating = False

        # Main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)

        # Header bar
        header = Adw.HeaderBar()
        self.main_box.append(header)

        # Refresh button
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.connect("clicked", self.on_refresh)
        header.pack_end(refresh_btn)

        # Scrolled content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.main_box.append(scrolled)

        # Content clamp
        clamp = Adw.Clamp()
        clamp.set_maximum_size(500)
        scrolled.set_child(clamp)

        # Content box
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        clamp.set_child(content)

        # Status banner
        self.status_banner = Adw.Banner()
        self.status_banner.set_title("Connecting to mouse...")
        content.append(self.status_banner)

        # Device Info group
        self.info_group = Adw.PreferencesGroup(title="Device Info")
        content.append(self.info_group)

        self.device_row = Adw.ActionRow(title="Device", subtitle="Not connected")
        self.info_group.add(self.device_row)

        self.firmware_row = Adw.ActionRow(title="Firmware", subtitle="-")
        self.info_group.add(self.firmware_row)

        self.battery_row = Adw.ActionRow(title="Battery", subtitle="-")
        self.info_group.add(self.battery_row)

        # DPI group
        dpi_group = Adw.PreferencesGroup(title="DPI Settings")
        content.append(dpi_group)

        # DPI with slider and spin button
        self.dpi_row = Adw.ActionRow(title="DPI")
        dpi_group.add(self.dpi_row)

        # DPI spin button
        self.dpi_spin = Gtk.SpinButton()
        self.dpi_spin.set_adjustment(Gtk.Adjustment(value=800, lower=100, upper=26000, step_increment=100, page_increment=400))
        self.dpi_spin.set_width_chars(5)
        self.dpi_spin.set_valign(Gtk.Align.CENTER)
        self.dpi_spin.connect("value-changed", self.on_dpi_spin_changed)
        self.dpi_row.add_suffix(self.dpi_spin)

        # DPI slider
        self.dpi_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 100, 6400, 100)
        self.dpi_scale.set_hexpand(True)
        self.dpi_scale.set_size_request(150, -1)
        self.dpi_scale.set_value(800)
        self.dpi_scale.set_draw_value(False)
        self.dpi_scale.set_round_digits(0)
        for dpi in [400, 800, 1600, 3200, 6400]:
            self.dpi_scale.add_mark(dpi, Gtk.PositionType.BOTTOM, None)
        self.dpi_scale.connect("value-changed", self.on_dpi_scale_changed)
        self.dpi_row.add_suffix(self.dpi_scale)

        # Stage selector
        self.stage_row = Adw.ComboRow(title="DPI Stage")
        stage_model = Gtk.StringList.new(["Stage 1", "Stage 2", "Stage 3", "Stage 4", "Stage 5", "Stage 6"])
        self.stage_row.set_model(stage_model)
        self.stage_row.connect("notify::selected", self.on_stage_changed)
        dpi_group.add(self.stage_row)

        # Performance group
        perf_group = Adw.PreferencesGroup(title="Performance")
        content.append(perf_group)

        # Motion Sync toggle
        self.motion_sync_row = Adw.SwitchRow(title="Motion Sync")
        self.motion_sync_row.connect("notify::active", self.on_motion_sync_changed)
        perf_group.add(self.motion_sync_row)

        # Angle Snap toggle
        self.angle_snap_row = Adw.SwitchRow(title="Angle Snapping")
        self.angle_snap_row.connect("notify::active", self.on_angle_snap_changed)
        perf_group.add(self.angle_snap_row)

        # Ripple Control toggle
        self.ripple_row = Adw.SwitchRow(title="Ripple Control")
        self.ripple_row.connect("notify::active", self.on_ripple_changed)
        perf_group.add(self.ripple_row)

        # LOD selector
        self.lod_row = Adw.ComboRow(title="Lift-off Distance")
        lod_model = Gtk.StringList.new(["0.7mm", "1mm", "2mm"])
        self.lod_row.set_model(lod_model)
        self.lod_row.connect("notify::selected", self.on_lod_changed)
        perf_group.add(self.lod_row)

        # Debounce slider
        self.debounce_row = Adw.ActionRow(title="Debounce", subtitle="3ms")
        perf_group.add(self.debounce_row)

        self.debounce_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 20, 1)
        self.debounce_scale.set_hexpand(True)
        self.debounce_scale.set_value(3)
        self.debounce_scale.set_draw_value(False)
        self.debounce_scale.connect("value-changed", self.on_debounce_changed)
        self.debounce_row.add_suffix(self.debounce_scale)

        # Initial load
        GLib.idle_add(self.load_device_info)

    def load_device_info(self):
        def do_load():
            if not self.device.connect():
                GLib.idle_add(self.show_error, "Mouse not found")
                return
            try:
                info = self.device.get_info()
                GLib.idle_add(self.update_ui, info)
            except Exception as e:
                GLib.idle_add(self.show_error, str(e))
            finally:
                self.device.disconnect()

        thread = threading.Thread(target=do_load)
        thread.daemon = True
        thread.start()

    def update_ui(self, info):
        self.updating = True

        self.status_banner.set_revealed(False)
        self.device_row.set_subtitle(f"Pulsar X3 ({self.device.mode} mode)")
        self.firmware_row.set_subtitle(f"Mouse: {info['mouse_fw']} | Dongle: {info['dongle_fw']}")
        self.battery_row.set_subtitle(f"{info['battery']}%")

        self.dpi_scale.set_value(min(info['dpi'], 6400))
        self.dpi_spin.set_value(info['dpi'])

        self.stage_row.set_selected(info['stage'] - 1)

        self.motion_sync_row.set_active(info['motion_sync'])
        self.angle_snap_row.set_active(info['angle_snap'])
        self.ripple_row.set_active(info['ripple_control'])

        lod_index = {0.7: 0, 1.0: 1, 2.0: 2}.get(info['lod'], 1)
        self.lod_row.set_selected(lod_index)

        self.debounce_scale.set_value(info['debounce'])
        self.debounce_row.set_subtitle(f"{info['debounce']}ms")

        self.updating = False

    def show_error(self, message):
        self.status_banner.set_title(f"Error: {message}")
        self.status_banner.set_button_label("")
        self.status_banner.set_revealed(True)

    def on_refresh(self, button):
        self.status_banner.set_title("Refreshing...")
        self.status_banner.set_revealed(True)
        self.load_device_info()

    def run_device_command(self, func, *args):
        if self.updating:
            return

        def do_command():
            if not self.device.connect():
                GLib.idle_add(self.show_error, "Mouse not found")
                return
            try:
                func(*args)
            except Exception as e:
                GLib.idle_add(self.show_error, str(e))
            finally:
                self.device.disconnect()

        thread = threading.Thread(target=do_command)
        thread.daemon = True
        thread.start()

    def on_dpi_scale_changed(self, scale):
        dpi = int(round(scale.get_value() / 100) * 100)
        if self.updating:
            return
        self.updating = True
        self.dpi_spin.set_value(dpi)
        self.updating = False
        self.run_device_command(self.device.set_dpi, dpi)

    def on_dpi_spin_changed(self, spin):
        dpi = int(spin.get_value())
        if self.updating:
            return
        self.updating = True
        if dpi <= 6400:
            self.dpi_scale.set_value(dpi)
        self.updating = False
        self.run_device_command(self.device.set_dpi, dpi)

    def on_stage_changed(self, row, param):
        stage = row.get_selected() + 1
        self.run_device_command(self.device.set_stage, stage)
        GLib.timeout_add(200, self.load_device_info)

    def on_motion_sync_changed(self, row, param):
        self.run_device_command(self.device.set_motion_sync, row.get_active())

    def on_angle_snap_changed(self, row, param):
        self.run_device_command(self.device.set_angle_snap, row.get_active())

    def on_ripple_changed(self, row, param):
        self.run_device_command(self.device.set_ripple_control, row.get_active())

    def on_lod_changed(self, row, param):
        lod_values = [0.7, 1.0, 2.0]
        lod = lod_values[row.get_selected()]
        self.run_device_command(self.device.set_lod, lod)

    def on_debounce_changed(self, scale):
        ms = int(scale.get_value())
        self.debounce_row.set_subtitle(f"{ms}ms")
        self.run_device_command(self.device.set_debounce, ms)


class PulsarApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.pulsar.x3control",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = PulsarWindow(self)
        self.window.present()


def main():
    app = PulsarApp()
    app.run([])


if __name__ == "__main__":
    main()
