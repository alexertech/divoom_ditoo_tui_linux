"""DOS-style main menu for Ditoo controller."""

from textual.widgets import Static, ListItem, ListView
from textual.containers import Vertical
from textual.app import ComposeResult


class MenuItem(ListItem):
    """A single menu item with DOS-style formatting."""

    DEFAULT_CSS = """
    MenuItem {
        height: 1;
        padding: 0 1;
        color: #8a8a8a;
    }
    MenuItem:hover {
        background: #16213e;
        color: #00d2ff;
    }
    MenuItem.-highlight {
        background: #0f3460;
        color: #00d2ff;
        text-style: bold;
    }
    """

    def __init__(self, label: str, action: str, hotkey: str = "", **kwargs):
        super().__init__(**kwargs)
        self.label_text = label
        self.action_name = action
        self.hotkey = hotkey

    def compose(self) -> ComposeResult:
        if self.hotkey:
            yield Static(f"  [{self.hotkey}]  {self.label_text}")
        else:
            yield Static(f"       {self.label_text}")


class MainMenu(Vertical):
    """DOS-style main menu with keyboard-driven navigation."""

    DEFAULT_CSS = """
    MainMenu {
        width: 100%;
        height: 100%;
        align: center middle;
    }

    #menu-box {
        width: 48;
        height: auto;
        max-height: 20;
        border: heavy #0f3460;
        background: #0d0d1a;
        padding: 1 2;
    }

    #menu-title {
        text-align: center;
        color: #e94560;
        text-style: bold;
        height: 1;
        margin-bottom: 1;
    }

    #menu-subtitle {
        text-align: center;
        color: #444466;
        height: 1;
        margin-bottom: 1;
    }

    #menu-list {
        height: auto;
        max-height: 10;
        margin-bottom: 1;
    }

    #menu-footer {
        text-align: center;
        color: #333344;
        height: 1;
    }
    """

    MENU_ITEMS = [
        ("Connect / Disconnect", "toggle_connection", "C"),
        ("Sync Device", "sync_all", "S"),
        ("Brightness", "brightness", "B"),
        ("Clock Faces", "clock_faces", "F"),
        ("Icon Browser", "icon_browser", "I"),
        ("Animations", "animation_browser", "A"),
        ("Sync Gallery", "sync_hot_gallery", "G"),
        ("Quit", "quit", "Q"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-box"):
            yield Static("DITOO CONTROL", id="menu-title")
            yield Static("Divoom Ditoo-Plus  v0.1", id="menu-subtitle")
            yield ListView(
                *[
                    MenuItem(label, action, hotkey)
                    for label, action, hotkey in self.MENU_ITEMS
                ],
                id="menu-list",
            )
            yield Static("[Enter] Select  |  Hotkey for quick access", id="menu-footer")
