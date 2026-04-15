"""Sync results display screen."""

from dataclasses import dataclass
from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import Vertical
from textual.app import ComposeResult


@dataclass
class SyncResult:
    """Data collected during a sync operation."""

    clock_ok: bool = False
    clock_time: str = "--:--:--"
    weather_ok: bool = False
    weather_temp: str = "--"
    weather_desc: str = "Unknown"
    weather_code: str = "-"
    weather_error: str = ""


class SyncScreen(ModalScreen[None]):
    """Modal showing sync results."""

    DEFAULT_CSS = """
    SyncScreen {
        align: center middle;
    }

    #sync-box {
        width: 44;
        height: 16;
        border: double #0f3460;
        background: #0a0a1a;
        padding: 1 2;
    }

    #sync-title {
        text-align: center;
        color: #e94560;
        text-style: bold;
        height: 1;
        margin-bottom: 1;
    }

    .sync-section {
        height: 1;
        color: #00d2ff;
        text-style: bold;
    }

    .sync-row {
        height: 1;
        color: #c4c4c4;
        padding: 0 2;
    }

    .sync-ok {
        color: #50fa7b;
    }

    .sync-fail {
        color: #ff5555;
    }

    #sync-help {
        text-align: center;
        color: #555555;
        height: 1;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("enter", "close", "Close"),
    ]

    def __init__(self, result: SyncResult):
        super().__init__()
        self._result = result

    def compose(self) -> ComposeResult:
        r = self._result

        clock_status = "OK" if r.clock_ok else "FAIL"
        clock_class = "sync-ok" if r.clock_ok else "sync-fail"

        weather_status = "OK" if r.weather_ok else "FAIL"
        weather_class = "sync-ok" if r.weather_ok else "sync-fail"

        with Vertical(id="sync-box"):
            yield Static("SYNC RESULTS", id="sync-title")

            yield Static(" Clock", classes="sync-section")
            yield Static(f"   Status    {clock_status}", classes=f"sync-row {clock_class}")
            yield Static(f"   Time      {r.clock_time}", classes="sync-row")

            yield Static("")
            yield Static(" Weather", classes="sync-section")
            yield Static(f"   Status    {weather_status}", classes=f"sync-row {weather_class}")
            if r.weather_ok:
                yield Static(f"   Temp      {r.weather_temp}C", classes="sync-row")
                yield Static(f"   Condition {r.weather_desc} (code {r.weather_code})", classes="sync-row")
            else:
                yield Static(f"   Error     {r.weather_error}", classes="sync-row")

            yield Static("[Enter/Esc] Close", id="sync-help")

    def action_close(self) -> None:
        self.dismiss(None)
