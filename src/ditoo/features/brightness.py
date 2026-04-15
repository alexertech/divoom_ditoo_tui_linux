"""Brightness and volume controls."""

from ditoo.bluetooth.connection import DitooConnection
from ditoo.bluetooth.protocol import DitooProtocol
from ditoo.logging_setup import get_logger

logger = get_logger(__name__)


class DisplayController:
    """Manages brightness and volume on Ditoo-Plus."""

    def __init__(self, connection: DitooConnection):
        self._conn = connection
        self._brightness: int = 50
        self._volume: int = 8

    @property
    def brightness(self) -> int:
        return self._brightness

    @property
    def volume(self) -> int:
        return self._volume

    def set_brightness(self, level: int) -> bool:
        """Set display brightness.

        Args:
            level: 0-100.

        Returns:
            True if command succeeded.
        """
        level = max(0, min(100, level))
        frame = DitooProtocol.set_brightness(level)
        success = self._conn.send(frame)
        if success:
            self._brightness = level
            logger.info(f"Brightness set to {level}")
        return success

    def set_volume(self, level: int) -> bool:
        """Set speaker volume.

        Args:
            level: 0-16.

        Returns:
            True if command succeeded.
        """
        level = max(0, min(16, level))
        frame = DitooProtocol.set_volume(level)
        success = self._conn.send(frame)
        if success:
            self._volume = level
            logger.info(f"Volume set to {level}")
        return success
