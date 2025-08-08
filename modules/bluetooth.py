from fabric.bluetooth import BluetoothClient, BluetoothDevice
from fabric.utils.helpers import exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from gi.repository import GLib
from loguru import logger

import modules.icons as icons


class BluetoothDeviceSlot(CenterBox):
    def __init__(self, device: BluetoothDevice, **kwargs):
        super().__init__(name="bluetooth-device", **kwargs)
        self.device = device
        self.device.connect("changed", self.on_changed)
        self.device.connect(
            "notify::closed", lambda *_: self.device.closed and self.destroy()
        )

        self.connection_label = Label(name="bluetooth-connection", markup=icons.bluetooth_disconnected)
        self.connect_button = Button(
            name="bluetooth-connect",
            label="Connect",
            on_clicked=self._safe_toggle_connection,
            style_classes=["connected"] if self.device.connected else None,
        )

        self.start_children = [
            Box(
                spacing=8,
                h_expand=True,
                h_align="fill",
                children=[
                    Image(icon_name=device.icon_name + "-symbolic", size=16),
                    Label(label=device.name, h_expand=True, h_align="start", ellipsization="end"),
                    self.connection_label,
                ],
            )
        ]
        self.end_children = self.connect_button

        self.device.emit("changed")

    def _safe_toggle_connection(self, *args):
        """Safely toggle connection without interrupting audio streams."""
        try:
            if self.device.connected:
                self.device.set_connected(False)
            else:
                self.device.set_connected(True)
                # Give device time to fully connect
                GLib.timeout_add(1000, self._ensure_audio_sink_ready)
        except Exception as e:
            logger.error(f"Bluetooth connection toggle failed: {e}")
            # Fallback to simple toggle
            self.device.set_connected(not self.device.connected)

    def _ensure_audio_sink_ready(self):
        """Ensure audio sink is ready after device connection."""
        try:
            # Restart audio subsystem to recognize the new device properly
            exec_shell_command_async("systemctl --user restart pipewire-pulse")
            logger.info("Audio subsystem restarted for bluetooth device")
        except Exception as e:
            logger.warning(f"Failed to restart audio subsystem: {e}")
        return False

    def on_changed(self, *_):
        self.connection_label.set_markup(
            icons.bluetooth_connected if self.device.connected else icons.bluetooth_disconnected
        )
        if self.device.connecting:
            self.connect_button.set_label("Connecting...")
        else:
            self.connect_button.set_label(
                "Disconnect" if self.device.connected else "Connect"
            )
        if self.device.connected:
            self.connect_button.add_style_class("connected")
        else:
            self.connect_button.remove_style_class("connected")
        return

class BluetoothConnections(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="bluetooth",
            spacing=4,
            orientation="vertical",
            **kwargs,
        )

        self.widgets = kwargs["widgets"]

        self.buttons = self.widgets.buttons.bluetooth_button
        self.bt_status_text = self.buttons.bluetooth_status_text
        self.bt_status_button = self.buttons.bluetooth_status_button
        self.bt_icon = self.buttons.bluetooth_icon
        self.bt_label = self.buttons.bluetooth_label
        self.bt_menu_button = self.buttons.bluetooth_menu_button
        self.bt_menu_label = self.buttons.bluetooth_menu_label

        self.client = BluetoothClient(on_device_added=self.on_device_added)
        self.scan_label = Label(name="bluetooth-scan-label", markup=icons.radar)
        self.scan_button = Button(
            name="bluetooth-scan",
            child=self.scan_label,
            tooltip_text="Scan for Bluetooth devices",
            on_clicked=lambda *_: self.client.toggle_scan()
        )
        self.back_button = Button(
            name="bluetooth-back",
            child=Label(name="bluetooth-back-label", markup=icons.chevron_left),
            on_clicked=lambda *_: self.widgets.show_notif()
        )

        self.client.connect("notify::enabled", lambda *_: self.status_label())
        self.client.connect(
            "notify::scanning",
            lambda *_: self.update_scan_label()
        )
        
        # Add bluetooth toggle functionality
        self.bt_status_button.connect(
            "clicked", 
            lambda *_: self.client.set_enabled(not self.client.enabled)
        )

        self.paired_box = Box(spacing=2, orientation="vertical")
        self.available_box = Box(spacing=2, orientation="vertical")

        content_box = Box(spacing=4, orientation="vertical")
        content_box.add(self.paired_box)
        content_box.add(Label(name="bluetooth-section", label="Available"))
        content_box.add(self.available_box)

        self.children = [
            CenterBox(
                name="bluetooth-header",
                start_children=self.back_button,
                center_children=Label(name="bluetooth-text", label="Bluetooth Devices"),
                end_children=self.scan_button
            ),
            ScrolledWindow(
                name="bluetooth-devices",
                min_content_size=(-1, -1),
                child=content_box,
                v_expand=True,
                propagate_width=False,
                propagate_height=False,
            ),
        ]

        self.client.notify("scanning")
        self.client.notify("enabled")

    def status_label(self):
        print(self.client.enabled)
        if self.client.enabled:
            self.bt_status_text.set_label("Enabled")
            for i in [self.bt_status_button, self.bt_status_text, self.bt_icon, self.bt_label, self.bt_menu_button, self.bt_menu_label]:
                i.remove_style_class("disabled")
            self.bt_icon.set_markup(icons.bluetooth)
        else:
            self.bt_status_text.set_label("Disabled")
            for i in [self.bt_status_button, self.bt_status_text, self.bt_icon, self.bt_label, self.bt_menu_button, self.bt_menu_label]:
                i.add_style_class("disabled")
            self.bt_icon.set_markup(icons.bluetooth_off)

    def on_device_added(self, client: BluetoothClient, address: str):
        if not (device := client.get_device(address)):
            return
        slot = BluetoothDeviceSlot(device)

        if device.paired:
            return self.paired_box.add(slot)
        return self.available_box.add(slot)

    def update_scan_label(self):
        if self.client.scanning:
            self.scan_label.add_style_class("scanning")
            self.scan_button.add_style_class("scanning")
            self.scan_button.set_tooltip_text("Stop scanning for Bluetooth devices")
        else:
            self.scan_label.remove_style_class("scanning")
            self.scan_button.remove_style_class("scanning")
            self.scan_button.set_tooltip_text("Scan for Bluetooth devices")
            self.scan_button.remove_style_class("scanning")
            self.scan_button.set_tooltip_text("Scan for Bluetooth devices")
