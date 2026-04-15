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
| `Q` | Quit |

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
  __main__.py          CLI entry point (argparse)
  config.py            TOML config with dataclass models
  bluetooth/
    connection.py      RFCOMM socket manager (thread-safe)
    protocol.py        Binary protocol encoder
  features/
    clock.py           Time sync
    weather.py         Open-Meteo fetch + push
    brightness.py      Brightness/volume control
    battery.py         Battery via upower/D-Bus
  ui/
    app.py             Main Textual app
    menu.py            DOS-style main menu
    status_bar.py      Connection/battery status
    controls_screen.py Brightness/volume modals
    clock_face_screen.py Clock style picker
    sync_screen.py     Sync results display
```

## Docs

- [`docs/protocol.md`](docs/protocol.md) — Ditoo-Plus Bluetooth protocol reference (all known commands)

## License

Private.
