"""Brightness and volume control overlay."""

from textual.screen import ModalScreen
from textual.widgets import Static, ProgressBar, Label
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult


class SliderBar(Static):
    """Simple text-based slider display."""

    DEFAULT_CSS = """
    SliderBar {
        height: 1;
        width: 100%;
        color: #e94560;
    }
    """

    def __init__(self, value: int = 50, max_value: int = 100, **kwargs):
        super().__init__(**kwargs)
        self._value = value
        self._max_value = max_value

    @property
    def value(self) -> int:
        return self._value

    def set_value(self, value: int) -> None:
        self._value = max(0, min(self._max_value, value))
        self.refresh()

    def render(self) -> str:
        bar_width = 30
        filled = int((self._value / self._max_value) * bar_width)
        empty = bar_width - filled
        return f"  [{'\u2588' * filled}{'\u2591' * empty}] {self._value:>3}/{self._max_value}"


class BrightnessScreen(ModalScreen[int | None]):
    """Modal for adjusting brightness."""

    DEFAULT_CSS = """
    BrightnessScreen {
        align: center middle;
    }

    #brightness-box {
        width: 50;
        height: 11;
        border: double #0f3460;
        background: #0a0a1a;
        padding: 1 2;
    }

    #brightness-title {
        text-align: center;
        color: #e94560;
        text-style: bold;
        height: 1;
    }

    #brightness-help {
        text-align: center;
        color: #555555;
        height: 2;
        padding: 1 0;
    }
    """

    BINDINGS = [
        ("left", "decrease", "Decrease"),
        ("right", "increase", "Increase"),
        ("enter", "confirm", "Confirm"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, current_value: int = 50):
        super().__init__()
        self._current = current_value

    def compose(self) -> ComposeResult:
        with Vertical(id="brightness-box"):
            yield Static("BRIGHTNESS", id="brightness-title")
            yield Static("")
            yield SliderBar(self._current, 100, id="brightness-slider")
            yield Static("")
            yield Static(
                "[Left/Right] Adjust  [Enter] Apply  [Esc] Cancel",
                id="brightness-help",
            )

    def action_increase(self) -> None:
        slider = self.query_one("#brightness-slider", SliderBar)
        slider.set_value(slider.value + 5)

    def action_decrease(self) -> None:
        slider = self.query_one("#brightness-slider", SliderBar)
        slider.set_value(slider.value - 5)

    def action_confirm(self) -> None:
        slider = self.query_one("#brightness-slider", SliderBar)
        self.dismiss(slider.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class VolumeScreen(ModalScreen[int | None]):
    """Modal for adjusting volume."""

    DEFAULT_CSS = """
    VolumeScreen {
        align: center middle;
    }

    #volume-box {
        width: 50;
        height: 11;
        border: double #0f3460;
        background: #0a0a1a;
        padding: 1 2;
    }

    #volume-title {
        text-align: center;
        color: #e94560;
        text-style: bold;
        height: 1;
    }

    #volume-help {
        text-align: center;
        color: #555555;
        height: 2;
        padding: 1 0;
    }
    """

    BINDINGS = [
        ("left", "decrease", "Decrease"),
        ("right", "increase", "Increase"),
        ("enter", "confirm", "Confirm"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, current_value: int = 8):
        super().__init__()
        self._current = current_value

    def compose(self) -> ComposeResult:
        with Vertical(id="volume-box"):
            yield Static("VOLUME", id="volume-title")
            yield Static("")
            yield SliderBar(self._current, 16, id="volume-slider")
            yield Static("")
            yield Static(
                "[Left/Right] Adjust  [Enter] Apply  [Esc] Cancel",
                id="volume-help",
            )

    def action_increase(self) -> None:
        slider = self.query_one("#volume-slider", SliderBar)
        slider.set_value(slider.value + 1)

    def action_decrease(self) -> None:
        slider = self.query_one("#volume-slider", SliderBar)
        slider.set_value(slider.value - 1)

    def action_confirm(self) -> None:
        slider = self.query_one("#volume-slider", SliderBar)
        self.dismiss(slider.value)

    def action_cancel(self) -> None:
        self.dismiss(None)
