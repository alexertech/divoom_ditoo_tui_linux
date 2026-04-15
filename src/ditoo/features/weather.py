"""Weather feature — fetch weather data and push to device.

Uses Open-Meteo API (free, no API key required).
"""

import httpx
from ditoo.bluetooth.connection import DitooConnection
from ditoo.bluetooth.protocol import DitooProtocol
from ditoo.config import WeatherConfig
from ditoo.logging_setup import get_logger

logger = get_logger(__name__)

# Map WMO weather codes to Ditoo-Plus weather icon codes.
# WMO codes: https://open-meteo.com/en/docs (weathercode section)
# Ditoo codes (confirmed via device testing):
#   0x01=Clear, 0x03=Cloudy, 0x05=Thunderstorm,
#   0x06=Rain, 0x08=Snow, 0x09=Fog
DITOO_CLEAR = 0x01
DITOO_CLOUDY = 0x03
DITOO_STORM = 0x05
DITOO_RAIN = 0x06
DITOO_SNOW = 0x08
DITOO_FOG = 0x09

WMO_TO_DIVOOM = {
    0: DITOO_CLEAR,    # Clear sky
    1: DITOO_CLEAR,    # Mainly clear
    2: DITOO_CLOUDY,   # Partly cloudy
    3: DITOO_CLOUDY,   # Overcast
    45: DITOO_FOG,     # Fog
    48: DITOO_FOG,     # Depositing rime fog
    51: DITOO_RAIN,    # Light drizzle
    53: DITOO_RAIN,    # Moderate drizzle
    55: DITOO_RAIN,    # Dense drizzle
    61: DITOO_RAIN,    # Slight rain
    63: DITOO_RAIN,    # Moderate rain
    65: DITOO_RAIN,    # Heavy rain
    66: DITOO_RAIN,    # Freezing rain light
    67: DITOO_RAIN,    # Freezing rain heavy
    71: DITOO_SNOW,    # Slight snow
    73: DITOO_SNOW,    # Moderate snow
    75: DITOO_SNOW,    # Heavy snow
    77: DITOO_SNOW,    # Snow grains
    80: DITOO_RAIN,    # Slight rain showers
    81: DITOO_RAIN,    # Moderate rain showers
    82: DITOO_RAIN,    # Violent rain showers
    85: DITOO_SNOW,    # Slight snow showers
    86: DITOO_SNOW,    # Heavy snow showers
    95: DITOO_STORM,   # Thunderstorm
    96: DITOO_STORM,   # Thunderstorm w/ slight hail
    99: DITOO_STORM,   # Thunderstorm w/ heavy hail
}

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherController:
    """Fetches weather and pushes to Ditoo-Plus."""

    def __init__(self, connection: DitooConnection, config: WeatherConfig):
        self._conn = connection
        self._config = config
        self._last_temp: int | None = None
        self._last_code: int | None = None
        self._last_description: str = "Unknown"

    @property
    def last_temperature(self) -> int | None:
        return self._last_temp

    @property
    def last_description(self) -> str:
        return self._last_description

    def fetch_and_push(self) -> tuple[bool, str]:
        """Fetch current weather from Open-Meteo and send to device.

        Returns:
            Tuple of (success, detail_message).
        """
        if not self._config.enabled:
            return False, "Weather disabled in config"

        if self._config.latitude == 0.0 and self._config.longitude == 0.0:
            return False, "Weather coordinates not configured"

        try:
            temp_unit = "fahrenheit" if self._config.unit == "fahrenheit" else "celsius"
            params = {
                "latitude": self._config.latitude,
                "longitude": self._config.longitude,
                "current_weather": "true",
                "temperature_unit": temp_unit,
            }
            with httpx.Client(timeout=10.0) as client:
                response = client.get(OPEN_METEO_URL, params=params)
                response.raise_for_status()
                data = response.json()

            current = data["current_weather"]
            temperature = int(round(current["temperature"]))
            wmo_code = current["weathercode"]
            divoom_code = WMO_TO_DIVOOM.get(wmo_code, DITOO_CLOUDY)

            self._last_temp = temperature
            self._last_code = divoom_code
            self._last_description = self._weather_description(divoom_code)

            frame = DitooProtocol.set_weather(temperature, divoom_code)
            success = self._conn.send(frame)
            if not success:
                return False, "Send failed"

            logger.info(
                f"Weather pushed: {temperature}deg {self._last_description}"
            )
            return True, f"{temperature}C {self._last_description}"

        except (httpx.HTTPError, KeyError, ValueError) as e:
            logger.error(f"Weather fetch failed: {e}")
            return False, f"Fetch error: {e}"

    @staticmethod
    def _weather_description(code: int) -> str:
        """Human-readable weather description."""
        descriptions = {
            DITOO_CLEAR: "Clear",
            DITOO_CLOUDY: "Cloudy",
            DITOO_STORM: "Storm",
            DITOO_RAIN: "Rain",
            DITOO_SNOW: "Snow",
            DITOO_FOG: "Fog",
        }
        return descriptions.get(code, "Unknown")
