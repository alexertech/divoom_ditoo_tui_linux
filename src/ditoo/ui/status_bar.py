"""Status bar showing device connection state and info."""

from textual.widgets import Static


class StatusBar(Static):
    """Top status bar with device info and battery."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: #0f3460;
        color: #00d2ff;
        text-style: bold;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__("DITOO CONTROL", *args, **kwargs)
        self._device_name: str = "Ditoo-Plus"
        self._connected: bool = False
        self._battery: int | None = None

    def on_mount(self) -> None:
        """Render initial state."""
        self._render_bar()

    def update_status(
        self,
        connected: bool,
        device_name: str = "",
        battery: int | None = None,
    ) -> None:
        """Update connection status display."""
        self._connected = connected
        if device_name:
            self._device_name = device_name
        self._battery = battery
        self._render_bar()

    def _render_bar(self) -> None:
        """Render the status bar content."""
        title = " DITOO"

        if self._connected:
            bat_str = f"BAT {self._battery}%" if self._battery is not None else "BAT --"
            status = f"{self._device_name}  {bat_str}  ONLINE "
        else:
            status = " OFFLINE "

        width = self.size.width if self.size.width > 0 else 80
        padding = width - len(title) - len(status)

        if padding > 0:
            content = f"{title}{' ' * padding}{status}"
        else:
            content = f"{title}  {status}"

        self.update(content)

    def on_resize(self, event) -> None:
        """Re-render on resize."""
        self._render_bar()
