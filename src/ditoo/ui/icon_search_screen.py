"""Icon browser screen — search, preview, and push game icons to device."""

from textual.screen import ModalScreen
from textual.widgets import Static, Input, ListView, ListItem
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult

from ditoo.features.icons import COLOR_PRESETS


class IconResultItem(ListItem):
    """A single icon search result."""

    DEFAULT_CSS = """
    IconResultItem {
        height: 1;
        padding: 0 2;
        color: #c4c4c4;
    }
    IconResultItem:hover {
        background: #16213e;
        color: #50fa7b;
    }
    """

    def __init__(self, author: str, name: str, **kwargs):
        super().__init__(**kwargs)
        self.author = author
        self.icon_name = name

    def compose(self) -> ComposeResult:
        display_name = self.icon_name.replace("-", " ").title()
        yield Static(f"  {display_name:<28} {self.author}")


class ColorItem(ListItem):
    """A color preset option."""

    DEFAULT_CSS = """
    ColorItem {
        height: 1;
        padding: 0 2;
        color: #c4c4c4;
    }
    ColorItem:hover {
        background: #16213e;
    }
    """

    def __init__(self, fg: str, bg: str, label: str, **kwargs):
        super().__init__(**kwargs)
        self.fg = fg
        self.bg = bg
        self.color_label = label

    def compose(self) -> ComposeResult:
        yield Static(f"  ██ {self.color_label}", classes=f"color-{self.color_label.lower()}")


# Result type: (author, icon_name, fg_hex, bg_hex) or None
IconSelection = tuple[str, str, str, str] | None


class IconSearchScreen(ModalScreen[IconSelection]):
    """Multi-step modal: search → select icon → pick color → confirm."""

    DEFAULT_CSS = """
    IconSearchScreen {
        align: center middle;
    }

    #icon-box {
        width: 56;
        height: 28;
        border: double #0f3460;
        background: #0a0a1a;
        padding: 1 2;
    }

    #icon-title {
        text-align: center;
        color: #e94560;
        text-style: bold;
        height: 1;
        margin-bottom: 1;
    }

    #icon-search-input {
        margin-bottom: 1;
    }

    #icon-status {
        height: 1;
        color: #446688;
        margin-bottom: 1;
    }

    #icon-results {
        height: 12;
    }

    #color-results {
        height: 8;
    }

    #icon-preview-box {
        height: 20;
    }

    #icon-preview-art {
        color: #50fa7b;
        height: 16;
    }

    #icon-help {
        text-align: center;
        color: #555555;
        height: 1;
        margin-top: 1;
    }

    .color-green { color: #50fa7b; }
    .color-red { color: #e94560; }
    .color-cyan { color: #00d2ff; }
    .color-pink { color: #ff79c6; }
    .color-white { color: #ffffff; }
    .color-yellow { color: #f1fa8c; }

    .hidden { display: none; }
    """

    BINDINGS = [
        ("escape", "back", "Back/Cancel"),
    ]

    def __init__(self, icon_index: list[str]):
        super().__init__()
        self._icon_index = icon_index
        self._phase = "search"  # search → color → preview
        self._selected_author = ""
        self._selected_name = ""
        self._selected_fg = ""
        self._selected_bg = ""
        self._preview_lines: list[str] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="icon-box"):
            yield Static("ICON BROWSER", id="icon-title")
            yield Input(
                placeholder="Search icons (e.g. brain, skull, fire)...",
                id="icon-search-input",
            )
            yield Static("3659 icons available", id="icon-status")
            yield ListView(id="icon-results")
            yield ListView(id="color-results", classes="hidden")
            yield Vertical(id="icon-preview-box", classes="hidden")
            yield Static("[Enter] Select  [Esc] Back", id="icon-help")

    def on_mount(self) -> None:
        self.query_one("#icon-search-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Live search as user types."""
        if self._phase != "search":
            return

        query = event.value.strip()
        results_view = self.query_one("#icon-results", ListView)
        status = self.query_one("#icon-status", Static)

        if len(query) < 2:
            results_view.clear()
            status.update(f"{len(self._icon_index)} icons available")
            return

        # Search
        from ditoo.features.icons import search_icons
        matches = search_icons(self._icon_index, query)

        results_view.clear()
        shown = matches[:20]
        for icon in shown:
            author, name = icon.split("/")
            results_view.append(IconResultItem(author, name))

        count_text = f"{len(matches)} matches"
        if len(matches) > 20:
            count_text += f" (showing first 20)"
        status.update(count_text)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Focus the results list when Enter is pressed in search."""
        if self._phase == "search":
            results = self.query_one("#icon-results", ListView)
            if len(results.children) > 0:
                results.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle selection in results or color list."""
        if self._phase == "search" and isinstance(event.item, IconResultItem):
            self._selected_author = event.item.author
            self._selected_name = event.item.icon_name
            self._show_color_picker()

        elif self._phase == "color" and isinstance(event.item, ColorItem):
            self._selected_fg = event.item.fg
            self._selected_bg = event.item.bg
            self._show_preview()

    def _show_color_picker(self) -> None:
        """Transition to color selection phase."""
        self._phase = "color"
        display = self._selected_name.replace("-", " ").title()

        # Hide search, show colors
        self.query_one("#icon-search-input", Input).add_class("hidden")
        self.query_one("#icon-results", ListView).add_class("hidden")
        self.query_one("#color-results", ListView).remove_class("hidden")

        self.query_one("#icon-title", Static).update(f"COLOR — {display}")
        self.query_one("#icon-status", Static).update("Pick a color theme")
        self.query_one("#icon-help", Static).update(
            "[Enter] Select  [Esc] Back to search"
        )

        color_list = self.query_one("#color-results", ListView)
        color_list.clear()
        for fg, bg, label in COLOR_PRESETS:
            color_list.append(ColorItem(fg, bg, label))
        color_list.focus()

    def _show_preview(self) -> None:
        """Transition to preview phase — download and show ASCII art."""
        self._phase = "preview"
        display = self._selected_name.replace("-", " ").title()

        self.query_one("#color-results", ListView).add_class("hidden")
        self.query_one("#icon-preview-box", Vertical).remove_class("hidden")
        self.query_one("#icon-title", Static).update(f"PREVIEW — {display}")
        self.query_one("#icon-status", Static).update("Downloading...")
        self.query_one("#icon-help", Static).update(
            "[Enter] Push to device  [Esc] Back to colors"
        )

        # Download and preview in worker thread
        self.run_worker(self._download_and_preview, thread=True)

    async def _download_and_preview(self) -> None:
        """Download icon and render preview."""
        from ditoo.features.icons import download_icon, render_ascii_preview

        try:
            img = download_icon(
                self._selected_author, self._selected_name,
                self._selected_fg, self._selected_bg,
            )
            self._preview_lines = render_ascii_preview(img)
            art_text = "\n".join(self._preview_lines)
            self.app.call_from_thread(self._update_preview, art_text)
        except Exception as e:
            self.app.call_from_thread(
                self._update_preview, f"Download failed: {e}"
            )

    def _update_preview(self, art: str) -> None:
        """Update the preview display."""
        preview_box = self.query_one("#icon-preview-box", Vertical)
        preview_box.remove_children()
        preview_box.mount(Static(art, id="icon-preview-art"))

        self.query_one("#icon-status", Static).update(
            f"{self._selected_author}/{self._selected_name}"
        )

        # Bind Enter to confirm at this phase
        self._bind_preview_confirm()

    def _bind_preview_confirm(self) -> None:
        """Set up Enter to confirm push."""
        # We use a key handler since we're past the ListView phase
        pass

    def on_key(self, event) -> None:
        """Handle Enter in preview phase to confirm."""
        if self._phase == "preview" and event.key == "enter":
            self.dismiss((
                self._selected_author,
                self._selected_name,
                self._selected_fg,
                self._selected_bg,
            ))

    def action_back(self) -> None:
        """Go back one phase or cancel."""
        if self._phase == "preview":
            # Back to color picker
            self.query_one("#icon-preview-box", Vertical).add_class("hidden")
            self._show_color_picker()

        elif self._phase == "color":
            # Back to search
            self._phase = "search"
            self.query_one("#color-results", ListView).add_class("hidden")
            self.query_one("#icon-search-input", Input).remove_class("hidden")
            self.query_one("#icon-results", ListView).remove_class("hidden")

            self.query_one("#icon-title", Static).update("ICON BROWSER")
            self.query_one("#icon-status", Static).update(
                f"{len(self._icon_index)} icons available"
            )
            self.query_one("#icon-help", Static).update(
                "[Enter] Select  [Esc] Cancel"
            )
            self.query_one("#icon-search-input", Input).focus()

        else:
            # Cancel entirely
            self.dismiss(None)
