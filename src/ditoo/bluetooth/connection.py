"""Bluetooth RFCOMM connection manager for Ditoo-Plus."""

import socket
import threading
from ditoo.logging_setup import get_logger

logger = get_logger(__name__)


class DitooConnection:
    """Manages Bluetooth RFCOMM connection to Ditoo-Plus device."""

    def __init__(self, mac_address: str, port: int = 1):
        self.mac_address = mac_address
        self.port = port
        self._socket: socket.socket | None = None
        self._lock = threading.Lock()
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """Establish RFCOMM connection to device.

        Returns:
            True if connection succeeded, False otherwise.
        """
        with self._lock:
            if self._connected:
                logger.warning("Already connected")
                return True

            try:
                self._socket = socket.socket(
                    socket.AF_BLUETOOTH,
                    socket.SOCK_STREAM,
                    socket.BTPROTO_RFCOMM,
                )
                self._socket.settimeout(10.0)
                logger.info(f"Connecting to {self.mac_address}:{self.port}")
                self._socket.connect((self.mac_address, self.port))
                self._socket.settimeout(5.0)
                self._connected = True
                logger.info("Connection established")
                return True
            except (OSError, socket.error) as e:
                logger.error(f"Connection failed: {e}")
                self._cleanup_socket()
                return False

    def disconnect(self) -> None:
        """Close the Bluetooth connection."""
        with self._lock:
            if self._socket is not None:
                logger.info("Disconnecting")
                self._cleanup_socket()
            self._connected = False

    def send(self, data: bytes) -> bool:
        """Send raw bytes to the device.

        Args:
            data: Raw bytes to send.

        Returns:
            True if send succeeded.
        """
        with self._lock:
            if not self._connected or self._socket is None:
                logger.error("Not connected")
                return False

            try:
                self._socket.sendall(data)
                logger.debug(f"Sent {len(data)} bytes: {data.hex()}")
                return True
            except (OSError, socket.error) as e:
                logger.error(f"Send failed: {e}")
                self._connected = False
                return False

    def receive(self, size: int = 1024) -> bytes | None:
        """Receive data from the device.

        Args:
            size: Maximum bytes to receive.

        Returns:
            Received bytes or None on failure.
        """
        with self._lock:
            if not self._connected or self._socket is None:
                return None

            try:
                data = self._socket.recv(size)
                logger.debug(f"Received {len(data)} bytes: {data.hex()}")
                return data
            except socket.timeout:
                return None
            except (OSError, socket.error) as e:
                logger.error(f"Receive failed: {e}")
                self._connected = False
                return None

    def _cleanup_socket(self) -> None:
        """Safely close and discard the socket."""
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
