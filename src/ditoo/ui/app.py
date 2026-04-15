"""Main Textual application for Ditoo controller."""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Static, ListView
from textual.containers import Container

from ditoo.bluetooth.connection import DitooConnection
from ditoo.features.clock import ClockController
from ditoo.features.weather import WeatherController
from ditoo.features.battery import read_battery
from ditoo.config import Config
from ditoo.logging_setup import get_logger
from ditoo.ui.status_bar import StatusBar
from ditoo.ui.menu import MainMenu, MenuItem

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
    ]

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self._connection = DitooConnection(
            mac_address=config.device.mac_address,
            port=config.device.rfcomm_port,
        )
        self._clock = ClockController(self._connection)
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
        weather_ok = self._weather.fetch_and_push()
        if weather_ok:
            temp = self._weather.last_temperature
            desc = self._weather.last_description
            results.append(f"Weather {temp}C {desc}")
        else:
            results.append("Weather FAIL")

        summary = "Synced: " + " | ".join(results)
        self.call_from_thread(self._log, summary)
        self.call_from_thread(self._update_status)

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
