<h1 align="center">Ditoo</h1>

<p align="center">
  Terminal controller for the Divoom Ditoo-Plus pixel art speaker.
</p>

---

## Features

- Bluetooth RFCOMM connection to Ditoo-Plus
- Clock sync (system time to device)
- Weather display (Open-Meteo API, no key required)
- Brightness control
- Clock face selection (6 styles)
- Channel switching (Clock, Lighting, Cloud, VJ, Visualizer, Custom)
- Icon browser — search 3600+ game icons, preview, and push to device
- Static image upload (16×16 pixel art via 0x44)
- Animation library — 13 curated GIFs, auto-crop sprite framing, push to device (0x49)
- Hot gallery sync — one-shot pull of Divoom's trending animation, auto-budgeted to fit the device
- Toast notifications for action feedback

## Usage

```bash
ditoo                           # Launch TUI
ditoo --generate-config         # Print example config
ditoo --mac AA:BB:CC:DD:EE:FF   # Override device MAC
ditoo --log-level DEBUG         # Verbose logging
```

### TUI Hotkeys

| Key | Action |
|-----|--------|
| `C` | Connect / Disconnect |
| `S` | Sync clock + weather |
| `B` | Brightness |
| `F` | Clock faces |
| `I` | Icon browser |
| `A` | Animation browser |
| `G` | Sync hot gallery |
| `Q` | Quit |

### Icon Browser

Press `I` to search [game-icons.net](https://game-icons.net) (3600+ icons by Lorc, Delapouite, et al). The flow:

1. **Search** — live filtering as you type
2. **Color** — pick a color preset (green, red, cyan, pink, white, yellow)
3. **Preview** — ASCII art preview of the 16×16 result
4. **Push** — sends to device as a static image on the Custom channel

Icons are downloaded as white-on-black PNGs (the only pre-rendered combo the site serves) and recolored client-side to the selected palette. The icon index (3659 entries from sitemap) is cached at `/tmp/ditoo_game_icons_index.txt` after first load.

### Standalone Tools

```bash
python icon_push.py brain       # Search + push icon from CLI
python search_and_push.py       # Tenor GIF search + push (animated/static)
python test_animation.py        # Animation upload test (0x49 chunked)
```

## Setup

```bash
git clone <repo-url> && cd ditto
poetry install
ditoo
```

## Configuration

Save to `~/.config/ditoo/config.toml`:

```toml
[device]
mac_address = "AA:BB:CC:DD:EE:FF"
name = "Ditoo-Plus"
rfcomm_port = 1

[weather]
enabled = true
latitude = -33.49
longitude = -70.57
update_interval_minutes = 30
unit = "celsius"

[logging]
level = "WARNING"
```

Generate a starter config with `ditoo --generate-config > ~/.config/ditoo/config.toml`.

## Architecture

```
src/ditoo/
  __main__.py             CLI entry point (argparse)
  config.py               TOML config with dataclass models
  logging_setup.py        Logging configuration
  bluetooth/
    connection.py          RFCOMM socket manager (thread-safe)
    protocol.py            Binary protocol encoder (no byte stuffing)
  features/
    clock.py               Time sync
    weather.py             Open-Meteo fetch + push (WMO → Ditoo codes)
    brightness.py          Brightness/volume control
    battery.py             Battery via upower/D-Bus
    icons.py               game-icons.net search, download, Divoom conversion
    animations.py          GIF → 0xAA frame converter (auto-bbox crop, quantize, bit-pack)
    library.py             Animation catalog loader (catalog.toml → AnimationEntry, load_animation)
    gallery.py             Divoom hot-gallery sync (cloud fetch, 0xAA decode, decimation, re-encode)
  ui/
    app.py                 Main Textual app + action handlers
    menu.py                DOS-style main menu
    status_bar.py          Connection/battery status
    controls_screen.py     Brightness/volume modals
    clock_face_screen.py   Clock style picker
    sync_screen.py         Sync results display
    icon_search_screen.py  Icon search → color → preview → push flow
    channel_screen.py      Channel switching
```

## Dev Notes

**Textual gotchas:**
- Do NOT name attributes `_display` on `App` subclasses — it shadows Textual's internal `App._display()` method. Use `_display_ctrl` or similar.
- `call_from_thread()` lives on `App`, not `Screen`. From a ModalScreen worker, use `self.app.call_from_thread()`.
- Use `self.notify()` for user-visible feedback (toast above footer), not a hidden Static log bar.

**Ditoo protocol gotchas:** See [`docs/protocol.md` § Ditoo-Specific Behaviors](docs/protocol.md#ditoo-specific-behaviors).

**Animation gotchas:**
- The `reset_palette` byte in 0xAA frame headers must always be `0x00` despite upstream source-docs claiming otherwise. Setting `0x01` triggers the device's "satellite crash" error animation. See `docs/protocol.md` § 0x44.
- Animation `total_len` is 16-bit — hard 64 KB ceiling for any single upload. The converter raises `ValueError` before submitting over-budget data.
- Source GIFs with small sprites in large backgrounds (e.g., a 16-px cat centered in a 960² frame) render as tiny dots on the 16×16 device. The auto-crop strategy in `animations.py` uses a union bounding box across all frames to detect the sprite and tighten the crop. See `docs/animations.md`.

## Docs

- [`docs/protocol.md`](docs/protocol.md) — Ditoo-Plus Bluetooth protocol reference
- [`docs/animations.md`](docs/animations.md) — Animation library design, conversion pipeline, and authoring guide
- [`docs/gallery.md`](docs/gallery.md) — Hot gallery sync (Divoom cloud fetch + decimation pipeline)

## Credits

- **Game icons** by [Lorc](https://lorcblog.blogspot.com), [Delapouite](https://delapouite.com), and [contributors](https://game-icons.net/about.html) — licensed under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)
- **Protocol** reverse-engineered from [hass-divoom](https://github.com/d03n3rfr1tz3/hass-divoom), [node-divoom-timebox-evo](https://github.com/RomRider/node-divoom-timebox-evo), [divoom-ditoo-pro-controller](https://github.com/andreas-mausch/divoom-ditoo-pro-controller), and live device testing

## License

MIT — see [LICENSE](LICENSE).
