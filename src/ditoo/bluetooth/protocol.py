"""Divoom Ditoo-Plus binary protocol encoder/decoder.

Frame format:
    [0x01] [length_lo] [length_hi] [payload...] [crc_lo] [crc_hi] [0x02]

- Header: 0x01 (start marker)
- Length: 16-bit LE, size of payload + 2 (CRC bytes)
- Payload: command byte + parameters
- CRC: 16-bit LE sum of (length_bytes + payload)
- Footer: 0x02 (end marker)

Note: The Ditoo-Plus does NOT use byte stuffing. Raw bytes are sent
between header and footer markers. Confirmed via hass-divoom project
and live device testing.
"""

from ditoo.logging_setup import get_logger

logger = get_logger(__name__)

# Frame delimiters
FRAME_HEADER = 0x01
FRAME_FOOTER = 0x02

# Command IDs
CMD_SET_VOLUME = 0x08
CMD_SET_DATETIME = 0x18
CMD_SET_CHANNEL = 0x45
CMD_GET_SETTINGS = 0x46
CMD_SET_WEATHER = 0x5F
CMD_SET_BRIGHTNESS = 0x74

# Channel IDs (what the device displays)
CHANNEL_CLOCK = 0x00
CHANNEL_LIGHTING = 0x01
CHANNEL_CLOUD = 0x02
CHANNEL_VJ = 0x03
CHANNEL_VISUALIZER = 0x04
CHANNEL_CUSTOM = 0x05

# Clock styles (used with set_clock)
CLOCK_FULLSCREEN = 0x00
CLOCK_RAINBOW = 0x01
CLOCK_BOXED = 0x02
CLOCK_ANALOG_SQUARE = 0x03
CLOCK_FULLSCREEN_NEG = 0x04
CLOCK_ANALOG_ROUND = 0x05


class DitooProtocol:
    """Encodes commands into Divoom wire format."""

    @staticmethod
    def _calculate_crc(data: bytes) -> int:
        """Calculate CRC as simple 16-bit sum of all bytes."""
        return sum(data) & 0xFFFF

    @staticmethod
    def _build_frame(payload: bytes) -> bytes:
        """Wrap payload in a complete Divoom frame.

        The Ditoo-Plus does NOT use byte stuffing (confirmed via
        hass-divoom and live device testing). Raw bytes are sent
        between the 0x01 header and 0x02 footer markers.

        Args:
            payload: Command byte(s) followed by parameters.

        Returns:
            Complete frame ready to send over RFCOMM.
        """
        # Length covers payload + 2 CRC bytes
        length = len(payload) + 2
        length_bytes = length.to_bytes(2, "little")

        # CRC covers length bytes + payload
        raw_inner = length_bytes + payload
        crc = DitooProtocol._calculate_crc(raw_inner)
        crc_bytes = crc.to_bytes(2, "little")

        frame = bytes([FRAME_HEADER]) + raw_inner + crc_bytes + bytes([FRAME_FOOTER])
        logger.debug(f"Built frame: {frame.hex()}")
        return frame

    @staticmethod
    def set_brightness(level: int) -> bytes:
        """Set display brightness.

        Args:
            level: Brightness 0-100.
        """
        level = max(0, min(100, level))
        return DitooProtocol._build_frame(bytes([CMD_SET_BRIGHTNESS, level]))

    @staticmethod
    def set_volume(level: int) -> bytes:
        """Set speaker volume.

        Args:
            level: Volume 0-16.
        """
        level = max(0, min(16, level))
        return DitooProtocol._build_frame(bytes([CMD_SET_VOLUME, level]))

    @staticmethod
    def set_datetime(
        year: int, month: int, day: int,
        hour: int, minute: int, second: int
    ) -> bytes:
        """Set device date and time.

        Protocol format: 0x18 YY YH MM DD HH MI SS
        where YY = year % 100, YH = year // 100.
        """
        year_lo = year % 100
        year_hi = year // 100
        payload = bytes([
            CMD_SET_DATETIME,
            year_lo, year_hi,
            month, day,
            hour, minute, second,
        ])
        return DitooProtocol._build_frame(payload)

    @staticmethod
    def set_channel(channel: int) -> bytes:
        """Switch the device display channel.

        Args:
            channel: One of CHANNEL_* constants.
        """
        return DitooProtocol._build_frame(bytes([CMD_SET_CHANNEL, channel]))

    @staticmethod
    def set_clock(
        style: int = CLOCK_FULLSCREEN,
        twentyfour: bool = True,
        show_weather: bool = True,
        show_temp: bool = True,
        show_calendar: bool = True,
        color_r: int = 0xFF,
        color_g: int = 0xFF,
        color_b: int = 0xFF,
    ) -> bytes:
        """Set clock display with style and options.

        Ditoo-Plus payload format (from hass-divoom):
            0x45 0x00 [24h_flag] [style] [activated] [weather] [temp] [calendar] R G B

        Args:
            style: One of CLOCK_* constants (0-15).
            twentyfour: Use 24-hour time format.
            show_weather: Show weather icon.
            show_temp: Show temperature.
            show_calendar: Show date/calendar.
            color_r/g/b: Clock color RGB (0-255 each).
        """
        payload = bytes([
            CMD_SET_CHANNEL, CHANNEL_CLOCK,
            0x01 if twentyfour else 0x00,  # 12h/24h time format
            style,
            0x01,  # clock activated
            0x01 if show_weather else 0x00,
            0x01 if show_temp else 0x00,
            0x01 if show_calendar else 0x00,
            color_r, color_g, color_b,
        ])
        return DitooProtocol._build_frame(payload)

    @staticmethod
    def set_weather(temperature: int, weather_code: int) -> bytes:
        """Set weather display data.

        Args:
            temperature: Temperature value (-128 to 127).
            weather_code: Divoom weather type (0=clear, 1=cloudy, 2=overcast,
                         3=rain, 4=snow, 5=fog, 6=storm).
        """
        # Temperature as unsigned byte (two's complement for negatives)
        temp_byte = temperature & 0xFF
        payload = bytes([CMD_SET_WEATHER, temp_byte, weather_code])
        return DitooProtocol._build_frame(payload)

    @staticmethod
    def get_settings() -> bytes:
        """Request current device settings."""
        return DitooProtocol._build_frame(bytes([CMD_GET_SETTINGS]))

    @staticmethod
    def set_visualizer(effect_number: int = 0) -> bytes:
        """Switch to audio visualizer channel.

        Args:
            effect_number: Visualizer effect index.
        """
        payload = bytes([CMD_SET_CHANNEL, CHANNEL_VISUALIZER, effect_number])
        return DitooProtocol._build_frame(payload)
