# Ditoo-Plus Bluetooth Protocol

Reverse-engineered RFCOMM binary protocol for the Divoom Ditoo-Plus pixel art speaker.

Sources: [hass-divoom](https://github.com/d03n3rfr1tz3/hass-divoom), [node-divoom-timebox-evo](https://github.com/RomRider/node-divoom-timebox-evo), [divoom-ditoo-pro-controller](https://github.com/andreas-mausch/divoom-ditoo-pro-controller), and live device testing.

---

## Frame Format

```
[0x01] [length_lo length_hi] [payload...] [crc_lo crc_hi] [0x02]
```

| Field | Size | Description |
|-------|------|-------------|
| Header | 1 byte | Always `0x01` |
| Length | 2 bytes | 16-bit LE. `len(payload) + 2` (includes CRC) |
| Payload | N bytes | Command byte + parameters |
| CRC | 2 bytes | 16-bit LE. `sum(length_bytes + payload) & 0xFFFF` |
| Footer | 1 byte | Always `0x02` |

**The Ditoo-Plus does NOT use byte stuffing.** Other Divoom devices (Timebox, Pixoo) escape `0x01`/`0x02`/`0x03` in the payload, but the Ditoo-Plus expects raw bytes. Confirmed via hass-divoom (`escapePayload=False`) and live testing.

---

## Implemented Commands

### 0x74 — Set Brightness

```
Payload: [0x74, level]
  level: 0-100
```

### 0x08 — Set Volume

```
Payload: [0x08, level]
  level: 0-16
```

### 0x18 — Set DateTime

```
Payload: [0x18, year_lo, year_hi, month, day, hour, minute, second]
  year_lo: year % 100
  year_hi: year // 100
```

### 0x45 — Set Channel

Simple channel switch:
```
Payload: [0x45, channel_id]
  0x00=Clock, 0x01=Lighting, 0x02=Cloud, 0x03=VJ, 0x04=Visualizer, 0x05=Custom
```

Clock face configuration:
```
Payload: [0x45, 0x00, 24h_flag, style, 0x01, show_weather, show_temp, show_calendar, R, G, B]
  24h_flag:      0x00=12h, 0x01=24h
  style:         0x00-0x05 (see Clock Styles below)
  0x01:          clock activated
  show_weather:  0x00/0x01
  show_temp:     0x00/0x01
  show_calendar: 0x00/0x01
  R, G, B:       clock color (0-255 each)
```

Clock styles: `0x00`=Fullscreen, `0x01`=Rainbow, `0x02`=Boxed, `0x03`=Analog Square, `0x04`=Fullscreen Neg, `0x05`=Analog Round.

### 0x5F — Set Weather

```
Payload: [0x5F, temperature, weather_code]
  temperature: 0-255 (unsigned byte, two's complement for negatives)
  weather_code: see Weather Codes below
```

Weather codes (confirmed via device testing):

| Code | Icon |
|------|------|
| 0x01 | Clear |
| 0x03 | Cloudy |
| 0x05 | Thunderstorm |
| 0x06 | Rain |
| 0x08 | Snow |
| 0x09 | Fog |

### 0x46 — Get Settings

```
Payload: [0x46]
Response: [0x04, 0x46, 0x55, ...22 bytes...]
  Byte 8: Brightness (0-100)
```

---

## Available but Not Yet Implemented

### Radio / Audio

| Cmd | Description | Payload |
|-----|-------------|---------|
| `0x05` | Radio on/off | `[0x05, enabled]` — 0x01=on, 0x00=off |
| `0x61` | Set FM frequency | `[0x61, freq_lo, freq_hi]` — 16-bit LE (e.g. 101.1 MHz = 1011) |
| `0x0A` | Play/pause | `[0x0A, state]` — 0x01=play, 0x00=pause |

### Keyboard LED (Ditoo-specific)

```
Payload: [0x23, mode, code]
  Toggle on/off:  [0x23, 0x02, 0x1D]
  Next effect:    [0x23, 0x01, 0x1C]
  Prev effect:    [0x23, 0x00, 0x1B]
```

### Alarm

```
Payload: [0x43, slot, enabled, hour, minute, weekday_mask, mode, trigger, freq_lo, freq_hi, volume]
  slot:          alarm number (0+)
  enabled:       0x01=on, 0x00=off
  weekday_mask:  bitmask, bits 0-6 = Sun-Sat
  mode:          0=music, 1-4=other sound types
  trigger:       1=music, 4=GIF
  volume:        0-100
```

### Sleep Mode

```
Payload: [0x40, sleeptime, mode, enabled, freq_lo, freq_hi, volume, R, G, B, brightness]
  sleeptime:  minutes until sleep
  enabled:    0x01=on, 0x00=off
  volume:     0-100
  brightness: 0-100
```

### Tools (0x72)

Countdown:
```
[0x72, 0x03, enabled, hours, minutes]
  enabled: 0x01=start, 0x00=stop
```

Stopwatch:
```
[0x72, 0x00, value]
  0x00=start, 0x01=pause, 0x02=reset
```

Noise meter:
```
[0x72, 0x02, state]
  0x01=start, 0x02=stop
```

Scoreboard:
```
[0x72, 0x01, 0x01, blue_lo, blue_hi, red_lo, red_hi]
  Scores: 0-999, 16-bit LE
```

### Lighting Mode

```
Payload: [0x45, 0x01, R, G, B, brightness, effect_type, power, 0x00, 0x00, 0x00]
  effect_type: 0=PlainColor, 1=Love, 2=Plants, 3=NoMosquito, 4=Sleeping
  power:       0x01=on, 0x00=off
```

Direct color set:
```
Payload: [0x47, R, G, B, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00]
```

### VJ Effects

```
Payload: [0x45, 0x03, effect_number]
  0=Sparkles, 1=Lava, 2=VerticalRainbowLines, 3=Drops, 4=RainbowSwirl,
  5=CMYFade, 6=RainbowLava, 7=PastelPatterns, 8=CMYWave, 9=Fire,
  10=Countdown, 11=PinkBlueFade, 12=RainbowPolygons, 13=PinkBlueWave,
  14=RainbowCross, 15=RainbowShapes
```

### Image Upload (16x16)

```
Payload: [0x44, 0x00, 0x0A, 0x0A, 0x04,
          0xAA,                         # frame start marker
          frame_len_lo, frame_len_hi,   # 16-bit LE
          0x00, 0x00, 0x00,
          num_colors,                   # palette size (0x00 = 256)
          ...color_data...,             # RGB triplets (3 bytes * num_colors)
          ...pixel_data...]             # palette indices, bit-packed LSB first

  bits_per_pixel = ceil(log2(num_colors))
  16x16 = 256 pixels total
```

### Animation Upload

```
Payload: [0x49, total_len_lo, total_len_hi, packet_number, ...frame_data...]

Per frame:
  [0xAA, frame_len_lo, frame_len_hi, duration_lo, duration_hi,
   reset_palette, num_colors, ...palette..., ...pixels...]

Max ~200 bytes per packet. Increment packet_number per chunk.
```

### Game Control

| Cmd | Description | Payload |
|-----|-------------|---------|
| `0xA0` | Launch game | `[0xA0, enabled, game_number]` |
| `0x17` | Key down | `[0x17, direction]` — 1=up, 2=down, 3=left, 4=right, 5=OK |
| `0x21` | Key up | `[0x21, direction]` |
| `0x88` | Key press | `[0x88, 0x00]` — "go"/start |

### Miscellaneous

| Cmd | Description | Payload |
|-----|-------------|---------|
| `0x2B` | Set temp unit (C/F) | `[0x2B, unit]` — 0x00=C, 0x01=F |
| `0x2D` | Set time format | `[0x2D, type]` |
| `0x54` | Memorial/reminder | `[0x54, slot, enabled, month, day, hour, minute, animate, ...text...]` |
| `0xBD` | Select design slot | `[0xBD, slot]` — 0, 1, or 2 |

### Screen Off (workaround)

No dedicated command. Use lighting mode with power off:
```
[0x45, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
```

---

## Device Response Format

The device ACKs recognized commands:
```
[0x01] [0x06 0x00] [0x04, echoed_cmd, 0x55, param] [crc_lo crc_hi] [0x02]
```

- `0x04` = response command
- `0x55` = acknowledgment status
- Commands like `set_weather` do NOT send ACKs

---

## Known Gaps

- No command found for querying battery level over RFCOMM (use upower/D-Bus instead)
- No command for firmware version query
- EQ/equalizer settings referenced but never reverse-engineered
- Lyrics display (`0x45, 0x06`) — Ditoo-specific, untested
