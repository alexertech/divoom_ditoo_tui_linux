"""Weather feature — fetch weather data and push to device.

Uses Open-Meteo API (free, no API key required).
"""

import httpx
from ditoo.bluetooth.connection import DitooConnection
from ditoo.bluetooth.protocol import DitooProtocol
from ditoo.config import WeatherConfig
from ditoo.logging_setup import get_logger

logger = get_logger(__name__)

# Map WMO weather codes to Divoom weather types
# WMO: https://open-meteo.com/en/docs (weathercode section)
# Divoom: 0=clear, 1=cloudy, 2=overcast, 3=rain, 4=snow, 5=fog, 6=storm
WMO_TO_DIVOOM = {
    0: 0,   # Clear sky -> clear
    1: 0,   # Mainly clear -> clear
    2: 1,   # Partly cloudy -> cloudy
    3: 2,   # Overcast -> overcast
    45: 5,  # Fog -> fog
    48: 5,  # Depositing rime fog -> fog
    51: 3,  # Light drizzle -> rain
    53: 3,  # Moderate drizzle -> rain
    55: 3,  # Dense drizzle -> rain
    61: 3,  # Slight rain -> rain
    63: 3,  # Moderate rain -> rain
    65: 3,  # Heavy rain -> rain
    66: 3,  # Freezing rain light -> rain
    67: 3,  # Freezing rain heavy -> rain
    71: 4,  # Slight snow -> snow
    73: 4,  # Moderate snow -> snow
    75: 4,  # Heavy snow -> snow
    77: 4,  # Snow grains -> snow
    80: 3,  # Slight rain showers -> rain
    81: 3,  # Moderate rain showers -> rain
    82: 3,  # Violent rain showers -> rain
    85: 4,  # Slight snow showers -> snow
    86: 4,  # Heavy snow showers -> snow
    95: 6,  # Thunderstorm -> storm
    96: 6,  # Thunderstorm w/ slight hail -> storm
    99: 6,  # Thunderstorm w/ heavy hail -> storm
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

    def fetch_and_push(self) -> bool:
        """Fetch current weather from Open-Meteo and send to device.

        Returns:
            True if weather was fetched and sent successfully.
        """
        if self._config.latitude == 0.0 and self._config.longitude == 0.0:
            logger.warning("Weather coordinates not configured")
            return False

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
            divoom_code = WMO_TO_DIVOOM.get(wmo_code, 1)

            self._last_temp = temperature
            self._last_code = divoom_code
            self._last_description = self._weather_description(divoom_code)

            frame = DitooProtocol.set_weather(temperature, divoom_code)
            success = self._conn.send(frame)
            if success:
                logger.info(
                    f"Weather pushed: {temperature}deg {self._last_description}"
                )
            return success

        except (httpx.HTTPError, KeyError, ValueError) as e:
            logger.error(f"Weather fetch failed: {e}")
            return False

    @staticmethod
    def _weather_description(code: int) -> str:
        """Human-readable weather description."""
        descriptions = {
            0: "Clear",
            1: "Cloudy",
            2: "Overcast",
            3: "Rain",
            4: "Snow",
            5: "Fog",
            6: "Storm",
        }
        return descriptions.get(code, "Unknown")
