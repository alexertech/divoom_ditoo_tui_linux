"""Main Textual application for Ditoo controller."""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Static, ListView
from textual.containers import Container

from ditoo.bluetooth.connection import DitooConnection
from ditoo.bluetooth.protocol import DitooProtocol
from ditoo.features.clock import ClockController
from ditoo.features.brightness import DisplayController
from ditoo.features.weather import WeatherController
from ditoo.features.battery import read_battery
from ditoo.config import Config
from ditoo.logging_setup import get_logger
from ditoo.ui.status_bar import StatusBar
from ditoo.ui.menu import MainMenu, MenuItem
from ditoo.ui.controls_screen import BrightnessScreen
from ditoo.ui.clock_face_screen import ClockFaceScreen

logger = get_logger(__name__)


class DitooApp(App):
    """Terminal controller for Divoom Ditoo-Plus."""

    TITLE = "Ditoo Control"

    CSS = """
    Screen {
        background: #0a0a1a;
        layout: vertical;
    }

    #status-bar {
        dock: top;
        height: 1;
    }

    #main-container {
        height: 1fr;
    }

    #log-bar {
        dock: bottom;
        height: 1;
        background: #111122;
        color: #446688;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("c", "toggle_connection", "Connect"),
        ("s", "sync_all", "Sync"),
        ("b", "brightness", "Brightness"),
        ("f", "clock_faces", "Clock Faces"),
    ]

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self._connection = DitooConnection(
            mac_address=config.device.mac_address,
            port=config.device.rfcomm_port,
        )
        self._clock = ClockController(self._connection)
        self._display_ctrl = DisplayController(self._connection)
        self._weather = WeatherController(self._connection, config.weather)
        self._status_bar: StatusBar | None = None
        self._log_bar: Static | None = None

    def compose(self) -> ComposeResult:
        yield StatusBar(id="status-bar")
        yield Container(MainMenu(), id="main-container")
        yield Static("Ready. Press [C] to connect.", id="log-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize references after mount."""
        self._status_bar = self.query_one("#status-bar", StatusBar)
        self._log_bar = self.query_one("#log-bar", Static)

    def _log(self, message: str) -> None:
        """Update the bottom log bar with a message."""
        if self._log_bar is not None:
            self._log_bar.update(f" {message}")

    def _read_battery(self) -> int | None:
        """Read battery level from system."""
        return read_battery(self.config.device.mac_address)

    def _update_status(self) -> None:
        """Refresh the status bar with current connection state."""
        if self._status_bar is not None:
            battery = self._read_battery() if self._connection.connected else None
            self._status_bar.update_status(
                connected=self._connection.connected,
                device_name=self.config.device.name,
                battery=battery,
            )

    # --- Actions ---

    def action_toggle_connection(self) -> None:
        """Connect or disconnect from the Ditoo-Plus."""
        if self._connection.connected:
            self._connection.disconnect()
            self._log("Disconnected.")
            self._update_status()
        else:
            self._log(f"Connecting to {self.config.device.mac_address}...")
            self.run_worker(self._connect_worker, thread=True)

    async def _connect_worker(self) -> None:
        """Run connection in worker thread to avoid blocking UI."""
        success = self._connection.connect()
        if success:
            self.call_from_thread(self._log, "Connected!")
            self.call_from_thread(self._update_status)
        else:
            self.call_from_thread(
                self._log,
                "Connection failed. Is the device paired and in range?"
            )
            self.call_from_thread(self._update_status)

    def action_sync_all(self) -> None:
        """Sync clock and weather to device."""
        if not self._connection.connected:
            self._log("Not connected. Press [C] to connect first.")
            return

        self._log("Syncing clock and weather...")
        self.run_worker(self._sync_worker, thread=True)

    async def _sync_worker(self) -> None:
        """Run full sync in background thread."""
        try:
            results = []

            # Sync clock
            clock_ok = self._clock.sync_time()
            if clock_ok:
                from datetime import datetime
                now = datetime.now().strftime("%H:%M:%S")
                results.append(f"Clock {now}")
            else:
                results.append("Clock FAIL")

            # Sync weather
            weather_ok, weather_detail = self._weather.fetch_and_push()
            if weather_ok:
                results.append(f"Weather {weather_detail}")
            else:
                results.append(f"Weather: {weather_detail}")

            summary = "Synced: " + " | ".join(results)
            self.call_from_thread(self._log, summary)
            self.call_from_thread(self._update_status)
        except Exception as e:
            self.call_from_thread(self._log, f"Sync error: {e}")

    def action_brightness(self) -> None:
        """Open brightness adjustment modal."""
        if not self._connection.connected:
            self._log("Not connected. Press [C] to connect first.")
            return

        def on_brightness_result(value: int | None) -> None:
            if value is not None:
                self.run_worker(
                    lambda: self._apply_brightness(value), thread=True
                )

        self.push_screen(
            BrightnessScreen(self._display_ctrl.brightness), on_brightness_result
        )

    def _apply_brightness(self, level: int) -> None:
        """Send brightness to device in worker thread."""
        success = self._display_ctrl.set_brightness(level)
        if success:
            self.call_from_thread(self._log, f"Brightness set to {level}%")
        else:
            self.call_from_thread(self._log, "Brightness change failed.")

    def action_clock_faces(self) -> None:
        """Open clock face selection modal."""
        if not self._connection.connected:
            self._log("Not connected. Press [C] to connect first.")
            return

        def on_clock_face_result(result: tuple[int, str] | None) -> None:
            if result is not None:
                style, name = result
                self.run_worker(
                    lambda: self._apply_clock_face(style, name), thread=True
                )

        self.push_screen(ClockFaceScreen(), on_clock_face_result)

    def _apply_clock_face(self, style: int, name: str) -> None:
        """Send clock face style to device in worker thread."""
        try:
            frame = DitooProtocol.set_clock(style=style)
            success = self._connection.send(frame)
            if success:
                self.call_from_thread(
                    self._log, f"Clock face: {name} ({len(frame)}b sent)"
                )
            else:
                self.call_from_thread(self._log, "Clock face: send failed")
        except Exception as e:
            self.call_from_thread(self._log, f"Clock face error: {e}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle menu item selection via Enter key."""
        item = event.item
        if isinstance(item, MenuItem):
            action_method = getattr(self, f"action_{item.action_name}", None)
            if action_method:
                action_method()

    def action_quit(self) -> None:
        """Clean up and exit."""
        if self._connection.connected:
            self._connection.disconnect()
        self.exit()
