"""Channel selection screen."""

from textual.screen import ModalScreen
from textual.widgets import Static, ListView, ListItem
from textual.containers import Vertical
from textual.app import ComposeResult

from ditoo.bluetooth.protocol import (
    CHANNEL_CLOCK,
    CHANNEL_LIGHTING,
    CHANNEL_CLOUD,
    CHANNEL_VJ,
    CHANNEL_VISUALIZER,
    CHANNEL_CUSTOM,
)


CHANNELS = [
    ("Clock", CHANNEL_CLOCK, "Display clock face"),
    ("Lighting", CHANNEL_LIGHTING, "Lighting effects"),
    ("Cloud Gallery", CHANNEL_CLOUD, "Online pixel art gallery"),
    ("VJ Effects", CHANNEL_VJ, "VJ animations"),
    ("Visualizer", CHANNEL_VISUALIZER, "Audio visualizer"),
    ("Custom", CHANNEL_CUSTOM, "Custom pixel art / animations"),
]


class ChannelItem(ListItem):
    """A channel option."""

    DEFAULT_CSS = """
    ChannelItem {
        height: 2;
        padding: 0 2;
        color: #c4c4c4;
    }
    ChannelItem:hover {
        background: #16213e;
        color: #e94560;
    }
    """

    def __init__(self, name: str, channel_id: int, description: str, **kwargs):
        super().__init__(**kwargs)
        self.channel_id = channel_id
        self._name = name
        self._description = description

    def compose(self) -> ComposeResult:
        yield Static(f"  {self._name:<20} {self._description}")


class ChannelScreen(ModalScreen[int | None]):
    """Modal for selecting display channel."""

    DEFAULT_CSS = """
    ChannelScreen {
        align: center middle;
    }

    #channel-box {
        width: 56;
        height: 16;
        border: double #0f3460;
        background: #0a0a1a;
        padding: 1 2;
    }

    #channel-title {
        text-align: center;
        color: #e94560;
        text-style: bold;
        height: 1;
    }

    #channel-help {
        text-align: center;
        color: #555555;
        height: 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="channel-box"):
            yield Static("SELECT CHANNEL", id="channel-title")
            yield Static("")
            yield ListView(
                *[
                    ChannelItem(name, cid, desc)
                    for name, cid, desc in CHANNELS
                ],
                id="channel-list",
            )
            yield Static("[Enter] Select  [Esc] Cancel", id="channel-help")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, ChannelItem):
            self.dismiss(item.channel_id)

    def action_cancel(self) -> None:
        self.dismiss(None)
