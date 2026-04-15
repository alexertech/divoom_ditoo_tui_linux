"""Clock face style selection screen."""

from textual.screen import ModalScreen
from textual.widgets import Static, ListView, ListItem
from textual.containers import Vertical
from textual.app import ComposeResult

from ditoo.bluetooth.protocol import (
    CLOCK_FULLSCREEN,
    CLOCK_RAINBOW,
    CLOCK_BOXED,
    CLOCK_ANALOG_SQUARE,
    CLOCK_FULLSCREEN_NEG,
    CLOCK_ANALOG_ROUND,
)


CLOCK_FACES = [
    ("Fullscreen", CLOCK_FULLSCREEN, "Digital fullscreen"),
    ("Rainbow", CLOCK_RAINBOW, "Rainbow digital"),
    ("Boxed", CLOCK_BOXED, "Bordered box"),
    ("Analog Square", CLOCK_ANALOG_SQUARE, "Square analog"),
    ("Fullscreen Neg", CLOCK_FULLSCREEN_NEG, "Inverted digital"),
    ("Analog Round", CLOCK_ANALOG_ROUND, "Round analog"),
]


class ClockFaceItem(ListItem):
    """A clock face option."""

    DEFAULT_CSS = """
    ClockFaceItem {
        height: 1;
        padding: 0 2;
        color: #c4c4c4;
    }
    ClockFaceItem:hover {
        background: #16213e;
        color: #e94560;
    }
    """

    def __init__(self, name: str, style_id: int, description: str, **kwargs):
        super().__init__(**kwargs)
        self.style_id = style_id
        self._name = name
        self._description = description

    def compose(self) -> ComposeResult:
        yield Static(f"  {self._name:<16} {self._description}")


class ClockFaceScreen(ModalScreen[tuple[int, str] | None]):
    """Modal for selecting clock face style."""

    DEFAULT_CSS = """
    ClockFaceScreen {
        align: center middle;
    }

    #clock-face-box {
        width: 48;
        height: 14;
        border: double #0f3460;
        background: #0a0a1a;
        padding: 1 2;
    }

    #clock-face-title {
        text-align: center;
        color: #e94560;
        text-style: bold;
        height: 1;
    }

    #clock-face-help {
        text-align: center;
        color: #555555;
        height: 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="clock-face-box"):
            yield Static("CLOCK FACES", id="clock-face-title")
            yield Static("")
            yield ListView(
                *[
                    ClockFaceItem(name, sid, desc)
                    for name, sid, desc in CLOCK_FACES
                ],
                id="clock-face-list",
            )
            yield Static("[Enter] Select  [Esc] Cancel", id="clock-face-help")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, ClockFaceItem):
            self.dismiss((item.style_id, item._name))

    def action_cancel(self) -> None:
        self.dismiss(None)
