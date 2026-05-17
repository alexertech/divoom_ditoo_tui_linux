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
from ditoo.ui.sync_screen import SyncScreen, SyncResult
from ditoo.ui.icon_search_screen import IconSearchScreen, IconSelection
from ditoo.ui.animation_browser_screen import AnimationBrowserScreen

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
        background: #111133;
        color: #00d2ff;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("c", "toggle_connection", "Connect"),
        ("s", "sync_all", "Sync"),
        ("b", "brightness", "Brightness"),
        ("f", "clock_faces", "Clock Faces"),
        ("i", "icon_browser", "Icons"),
        ("a", "animation_browser", "Animations"),
        ("g", "sync_hot_gallery", "Sync gallery"),
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
        self._icon_index: list[str] | None = None

    def compose(self) -> ComposeResult:
        yield StatusBar(id="status-bar")
        yield Container(MainMenu(), id="main-container")
        yield Static("Ready. Press [C] to connect.", id="log-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize references after mount."""
        self._status_bar = self.query_one("#status-bar", StatusBar)
        self._log_bar = self.query_one("#log-bar", Static)

    def _log(self, message: str, severity: str = "information") -> None:
        """Show a toast notification above the footer bar."""
        self.notify(message, severity=severity, timeout=4)

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
            from datetime import datetime

            result = SyncResult()

            # Sync clock
            result.clock_ok = self._clock.sync_time()
            if result.clock_ok:
                result.clock_time = datetime.now().strftime("%H:%M:%S")

            # Sync weather
            weather_ok, weather_detail = self._weather.fetch_and_push()
            result.weather_ok = weather_ok
            if weather_ok:
                result.weather_temp = str(self._weather.last_temperature)
                result.weather_desc = self._weather.last_description
                result.weather_code = str(self._weather._last_code)
            else:
                result.weather_error = weather_detail

            self.call_from_thread(self._show_sync_result, result)
            self.call_from_thread(self._update_status)
        except Exception as e:
            self.call_from_thread(self._log, f"Sync error: {e}")

    def _show_sync_result(self, result: SyncResult) -> None:
        """Display sync results modal."""
        self.push_screen(SyncScreen(result))
        if result.clock_ok and result.weather_ok:
            self._log("Sync complete.")
        else:
            self._log("Sync completed with errors.")

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

    def action_icon_browser(self) -> None:
        """Open the icon browser modal."""
        if not self._connection.connected:
            self._log("Not connected. Press [C] to connect first.")
            return

        # Lazy-load the icon index
        if self._icon_index is None:
            self._log("Loading icon index...")
            self.run_worker(self._load_index_and_show, thread=True)
        else:
            self._show_icon_screen()

    async def _load_index_and_show(self) -> None:
        """Load icon index in background, then show the screen."""
        from ditoo.features.icons import load_or_build_index
        try:
            self._icon_index = load_or_build_index()
            self.call_from_thread(self._log, f"Loaded {len(self._icon_index)} icons")
            self.call_from_thread(self._show_icon_screen)
        except Exception as e:
            self.call_from_thread(self._log, f"Icon index failed: {e}")

    def _show_icon_screen(self) -> None:
        """Display the icon search modal."""
        def on_icon_result(result: IconSelection) -> None:
            if result is not None:
                author, name, fg, bg = result
                self.run_worker(
                    lambda: self._push_icon(author, name, fg, bg),
                    thread=True,
                )

        self.push_screen(IconSearchScreen(self._icon_index or []), on_icon_result)

    def _push_icon(self, author: str, name: str, fg: str, bg: str) -> None:
        """Download, convert, and push icon to device in worker thread."""
        from ditoo.features.icons import download_icon, image_to_divoom_frame

        try:
            display = name.replace("-", " ").title()
            self.call_from_thread(self._log, f"Pushing {display}...")

            img = download_icon(author, name, fg, bg)
            frame_data = image_to_divoom_frame(img)

            # Switch to custom channel
            channel_frame = DitooProtocol.set_channel(0x05)
            self._connection.send(channel_frame)

            import time
            time.sleep(0.3)

            # Push static image via 0x44
            payload = bytes([0x44, 0x00, 0x0A, 0x0A, 0x04]) + frame_data
            image_frame = DitooProtocol._build_frame(payload)
            success = self._connection.send(image_frame)

            if success:
                self.call_from_thread(
                    self._log,
                    f"Icon pushed: {display} ({len(image_frame)}b)",
                )
            else:
                self.call_from_thread(self._log, "Icon push failed")

        except Exception as e:
            self.call_from_thread(self._log, f"Icon error: {e}")

    def action_animation_browser(self) -> None:
        """Open the animation browser modal."""
        if not self._connection.connected:
            self._log("Not connected. Press [C] to connect first.")
            return

        self.push_screen(AnimationBrowserScreen())

    def action_sync_hot_gallery(self) -> None:
        """Fetch, decode, and push the top Divoom hot-gallery animation."""
        if not self.config.divoom.is_configured:
            self.notify(
                "Divoom credentials not configured — see docs/gallery.md",
                severity="warning",
            )
            return

        if not self._connection.connected:
            self._log("Not connected. Press [C] to connect first.")
            return

        self._log("Logging in to Divoom...")
        self.run_worker(self._gallery_worker, thread=True)

    def _gallery_worker(self) -> None:
        """Fetch, validate, and upload the hot gallery animation (worker thread)."""
        import time
        from ditoo.features.gallery import (
            GalleryError,
            GalleryValidationError,
            sync_hot_gallery,
        )
        from ditoo.bluetooth.protocol import DitooProtocol, MAX_ANIMATION_BYTES

        connection = self._connection
        email = self.config.divoom.email
        password_md5 = self.config.divoom.password_md5

        try:
            self.call_from_thread(self._log, "Fetching hot gallery...")
            data = sync_hot_gallery(email, password_md5)
            total_len = len(data)

            # Safety: with 200-byte chunks the packet_num field overflows at 256 packets.
            # The gallery clipper enforces this upstream; this assertion catches future
            # code paths that bypass it.
            chunk_size = 200
            total_packets = (total_len + chunk_size - 1) // chunk_size
            if total_packets > 256:
                raise ValueError(
                    f"Upload would need {total_packets} packets, exceeds 8-bit packet_num "
                    f"ceiling of 256. Cap data at MAX_ANIMATION_BYTES ({MAX_ANIMATION_BYTES}) bytes."
                )

            self.call_from_thread(
                self._log,
                f"Pushing {total_len // 1024} KB to device...",
            )

            # Switch to Custom channel
            channel_frame = DitooProtocol.set_channel(0x05)
            if not connection.send(channel_frame):
                raise RuntimeError("Failed to switch to Custom channel")
            time.sleep(0.3)

            # Drain any pending responses
            self._gallery_drain(connection)

            # Chunked 0x49 upload (same protocol as AnimationBrowserScreen)
            delay = 0.08 if total_len > 50_000 else 0.05
            packet_num = 0
            offset = 0

            while offset < total_len:
                chunk = data[offset:offset + chunk_size]
                payload = bytes([
                    0x49,
                    total_len & 0xFF,
                    (total_len >> 8) & 0xFF,
                    packet_num & 0xFF,
                ]) + chunk

                frame = DitooProtocol._build_frame(payload)
                if not connection.send(frame):
                    raise RuntimeError(f"Upload failed at packet {packet_num}")

                offset += chunk_size
                packet_num = (packet_num + 1) & 0xFF

                if packet_num % 10 == 0:
                    self._gallery_drain(connection)

                time.sleep(delay)

            time.sleep(0.5)
            self._gallery_drain(connection)

            self.call_from_thread(self._log, "Sync complete")

        except GalleryValidationError as exc:
            logger.error("Gallery validation failed: %s", exc)
            self.call_from_thread(
                self.notify, str(exc), severity="error", timeout=10
            )
            self.call_from_thread(self._log, f"Sync failed: {exc}", "error")
        except GalleryError as exc:
            logger.error("Gallery sync failed: %s", exc)
            self.call_from_thread(self._log, f"Sync failed: {exc}", "error")
        except Exception as exc:
            logger.error("Gallery sync unexpected error: %s", exc)
            self.call_from_thread(self._log, f"Sync failed: {exc}", "error")

    @staticmethod
    def _gallery_drain(connection) -> None:
        """Drain pending device ACKs (best-effort, non-blocking)."""
        try:
            sock = connection._sock
            if sock is None:
                return
            sock.setblocking(False)
            try:
                while True:
                    chunk = sock.recv(256)
                    if not chunk:
                        break
            except Exception:
                pass
            finally:
                sock.setblocking(True)
        except Exception:
            pass

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
