"""Battery level reader via D-Bus/upower."""

import subprocess
from ditoo.logging_setup import get_logger

logger = get_logger(__name__)


def read_battery(mac_address: str) -> int | None:
    """Read battery percentage for a Bluetooth device via upower.

    Args:
        mac_address: Device MAC address (e.g. "11:75:58:13:EE:12").

    Returns:
        Battery percentage (0-100) or None if unavailable.
    """
    mac_underscore = mac_address.replace(":", "_")
    device_path = f"/org/freedesktop/UPower/devices/headset_dev_{mac_underscore}"

    try:
        result = subprocess.run(
            ["upower", "-i", device_path],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode != 0:
            logger.debug(f"upower returned {result.returncode}")
            return None

        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("percentage:"):
                pct_str = line.split(":")[1].strip().rstrip("%")
                return int(pct_str)

    except (subprocess.TimeoutExpired, ValueError, OSError) as e:
        logger.debug(f"Battery read failed: {e}")

    return None
