# Ditoo-Plus Bluetooth Protocol

Reverse-engineered RFCOMM binary protocol for the Divoom Ditoo-Plus pixel art speaker.

Sources: [hass-divoom](https://github.com/d03n3rfr1tz3/hass-divoom), [node-divoom-timebox-evo](https://github.com/RomRider/node-divoom-timebox-evo), [divoom-ditoo-pro-controller](https://github.com/andreas-mausch/divoom-ditoo-pro-controller), and live device testing.

**Device:** A81-DITTO-PLUS · 16×16 pixel screen · Bluetooth RFCOMM

---

## Ditoo-Specific Behaviors

These differ from other Divoom devices (Timebox, Pixoo) and will break your code if you copy from those projects:

1. **No byte stuffing.** The Ditoo-Plus sends raw bytes between 0x01/0x02 frame markers. Other devices escape 0x01/0x02/0x03 in the payload — applying that escaping to the Ditoo corrupts every command containing those byte values.
2. **Weather codes are unique.** The Ditoo uses 0x01=Clear, 0x03=Cloudy, 0x05=Storm, 0x06=Rain, 0x08=Snow, 0x09=Fog. Generic Divoom code tables (0=clear, 1=cloudy, etc.) produce wrong icons.
3. **set_clock format differs from Timebox Evo.** Byte 2 is the 24h flag (not a sub-command), byte 4 is "clock activated" (not show_time). See 0x45 section below.
4. **set_weather (0x5F) does NOT send an ACK.** Most other commands ACK with `0x55`.
5. **No battery query over RFCOMM.** Use upower/D-Bus on the host system instead.

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

### 0x44 — Static Image Upload (16×16) ✅ Confirmed

Pushes a single-frame image to the Custom channel.

```
Payload: [0x44, 0x00, 0x0A, 0x0A, 0x04, ...animation_frame...]
```

Animation frame format:
```
[0xAA, frame_len_lo, frame_len_hi, duration_lo, duration_hi,
 reset_palette, num_colors, ...palette_rgb..., ...pixel_data...]

  frame_len:    total frame size in bytes (including this 7-byte header)
  duration:     16-bit LE, milliseconds (0 for static)
  reset_palette: 0x00 always. Despite source-doc claims that subsequent frames
                 use 0x01, both icons.py and test_animation.py reference
                 implementations hardcode 0x00 and the device accepts them.
                 Setting 0x01 produces the "satellite crash" malformed-data
                 response — likely the device interprets 0x01 as "palette
                 omitted; reuse prior" and then mis-parses palette bytes as
                 pixel data. Confirmed empirically 2026-05-15.
  num_colors:   palette size (0x00 = 256)
  palette_rgb:  num_colors × 3 bytes (R, G, B)
  pixel_data:   bit-packed palette indices, LSB first
                bits_per_pixel = ceil(log2(num_colors))
                16×16 = 256 pixels total
```

**Byte-5 / byte-6 layout (empirical, 2026-05-16):**

Files downloaded from the Divoom cloud gallery carry `reset_palette = 0x01` at byte 5 on all frames after the first, and `num_colors` at byte 6 — the same header layout documented above. Frame 0 of the tested 587KB file has `byte5 = 0x00` (reset_palette), `byte6 = 0x14` (num_colors = 20): `7 + 3*20 + ceil(5*256/8) = 7 + 60 + 160 = 227` bytes, matching `frame_len` exactly.

Frames 1+ have `byte5 = 0x01` (reset_palette set). The device accepts `0x01` from gallery files but rejects it when our local encoder sends it — likely because gallery frames carry a full palette after `0x01` whereas the device interprets `0x01` from the local path as "palette omitted; reuse prior," causing the mis-parse described in the `reset_palette` note above.

For gallery files, `gallery.py::find_clip_offset` trusts `frame_len` (bytes 1-2 LE) as the sole source of truth for frame boundaries and does not inspect `reset_palette` or `num_colors` at all — sidestepping both the byte-5/byte-6 ambiguity and the `reset_palette` question entirely.

Device ACKs with `0x44 0x55` on success.

### 0x46 — Get Settings

```
Payload: [0x46]
Response: [0x04, 0x46, 0x55, ...22 bytes...]
  Byte 8: Brightness (0-100)
```

---

## Partially Tested Commands

### 0x49 — Animation Upload (chunked)

Sends multi-frame animations in chunks. Each packet:

```
Payload: [0x49, total_len_lo, total_len_hi, packet_number, ...data_chunk...]
  total_len:     16-bit LE total animation data size
  packet_number: increments per chunk, wraps at 0xFF
  data_chunk:    max ~200 bytes of animation frame data
```

Animation data is concatenated frames using the same 0xAA format as 0x44.

**What works (confirmed 2026-05-15):**
- 178-frame animation (21,348 bytes, `knight.gif` after auto-crop + 4 bpp quantize) uploads
  and plays correctly at 50ms inter-packet delay (~107 packets, ~5.4s upload)
- 2-frame test animation (~84 bytes) works at 50ms delay
- `packet_number` must wrap at 0xFF: use `packet_num & 0xFF` (bare `bytes([n])` raises ValueError for n>255)
- Drain device ACKs every ~10 packets to prevent receive buffer buildup
- The empirical pacing rule in `test_animation.py` (50ms for ≤50KB, 80ms for >50KB) is sound
  at the small end; the >50KB threshold is unverified beyond the 21KB ceiling reached in testing
- **`packet_num` is 8-bit on 16×16 devices.** Verified via hass-divoom source
  (`index.to_bytes(1, ...)` for `screensize != 32`). Total packets per upload must be ≤256 →
  at 200-byte chunk size, **effective max animation size is 51,200 bytes**, NOT the 16-bit
  `total_len` value of 65,535. Exceeding 256 packets causes `packet_num` to wrap (0..255,
  0..70 etc.) and the device misinterprets the wrap as either a new-animation-start or a
  "missing packets, wait for more" state — observed as the "loading circle" UI followed by
  hang and satellite-crash on disconnect. `MAX_ANIMATION_BYTES = 51_000` (with a small margin)
  is enforced in `protocol.py` and applied by the gallery clipper.

**What breaks:**
- `total_len` is 16-bit — files >65KB overflow (587KB file sends 63,923 as length). **Hard blocker for large files.**
- Sending at full speed causes socket buffer overflow (failed at packet 287 of ~3000)
- Setting `reset_palette = 0x01` on any frame triggers the "satellite crash" error animation
  (see 0x44 § reset_palette note above) — empirically this byte must always be `0x00`
- Divoom gallery files can be enormous (tested: 3687 frames, 587KB, 434s of animation) — impractical over RFCOMM
- Device shows "satellite crash" error animation when upload data is malformed
- Uploading >256 chunks (>~51 KB at 200-byte chunk size) wraps the 8-bit `packet_num` field
  and causes the device to enter the "loading circle" state, hang, and show satellite-crash on
  disconnect. Use `MAX_ANIMATION_BYTES` (51,000 bytes) as the upload ceiling.

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

## Divoom Cloud API

Gallery content can be fetched from Divoom's servers (requires account).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `appin.divoom-gz.com/UserLogin` | POST | Login (email + MD5 password) |
| `app.divoom-gz.com/GetHotFilesV2` | POST | Browse hot gallery files |
| `app.divoom-gz.com/Discover/GetAlbumList` | POST | List gallery albums (44 categories) |
| `app.divoom-gz.com/Channel/GetDialType` | POST | List dial/clock types (25 categories) |
| `f.divoom-gz.com/{FileId}` | GET | Download raw animation data |

Login returns `Token` + `UserId` used for authenticated endpoints. `GetHotFilesV2` returns `FileList` with `FileId` strings (path-like, e.g. `group1/M00/9C/E1/...`). `DeviceType: 5` = Ditoo.

Gallery files use the same 0xAA frame format as the 0x44/0x49 commands. Tested file: 587KB, 3687 frames, 434s total animation, frame sizes 7-1025 bytes, durations 50-500ms. Files are raw concatenated 0xAA frames — no container header.

**Dead ends (tested, don't bother):**
- `SearchGalleryV2` — accepts requests but always returns empty `FileList` regardless of parameters (`Keyword`, `TagName`, `SearchText`, etc.)
- `Discover/GetAlbumImageList` — returns `ReturnCode: 1` (Failed) for all parameter combos
- `Channel/GetDialList` — returns `ReturnCode: 3` for all `DialType`/`Type` values
- `GetHotFilesV2` ignores filter params — same 3 files returned regardless of `TagName`, `Category`, `AlbumId`

---

## Known Gaps

- No command for querying battery level over RFCOMM (use upower/D-Bus instead)
- No command for firmware version query
- EQ/equalizer settings referenced but never reverse-engineered
- Lyrics display (`0x45, 0x06`) — Ditoo-specific, untested
- Animation upload (0x49) unreliable for large files (>65KB total_len overflow)
