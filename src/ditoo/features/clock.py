"""Clock feature — sync time and manage clock faces."""

from datetime import datetime
from ditoo.bluetooth.connection import DitooConnection
from ditoo.bluetooth.protocol import DitooProtocol, CHANNEL_CLOCK
from ditoo.logging_setup import get_logger

logger = get_logger(__name__)


class ClockController:
    """Manages clock display on Ditoo-Plus."""

    def __init__(self, connection: DitooConnection):
        self._conn = connection

    def sync_time(self) -> bool:
        """Sync device time to system clock.

        Returns:
            True if sync succeeded.
        """
        now = datetime.now()
        frame = DitooProtocol.set_datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=now.hour,
            minute=now.minute,
            second=now.second,
        )
        success = self._conn.send(frame)
        if success:
            logger.info(f"Time synced to {now.strftime('%Y-%m-%d %H:%M:%S')}")
        return success

    def show_clock(self) -> bool:
        """Switch device to clock channel.

        Returns:
            True if command succeeded.
        """
        frame = DitooProtocol.set_channel(CHANNEL_CLOCK)
        return self._conn.send(frame)
