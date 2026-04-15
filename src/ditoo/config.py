"""Configuration management for ditoo."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import tomllib


@dataclass
class DeviceConfig:
    """Bluetooth device configuration."""

    mac_address: str = "11:75:58:13:EE:12"
    name: str = "Ditoo-Plus"
    rfcomm_port: int = 1


@dataclass
class WeatherConfig:
    """Weather feature configuration."""

    enabled: bool = True
    latitude: float = -33.49
    longitude: float = -70.57
    update_interval_minutes: int = 30
    unit: Literal["celsius", "fahrenheit"] = "celsius"


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "WARNING"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class Config:
    """Master configuration for ditoo."""

    device: DeviceConfig = field(default_factory=DeviceConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_toml(cls, path: Path) -> "Config":
        """Load configuration from TOML file."""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"Invalid TOML in {path}: {e}")

        device_data = data.get("device", {})
        weather_data = data.get("weather", {})
        logging_data = data.get("logging", {})

        try:
            return cls(
                device=DeviceConfig(**device_data),
                weather=WeatherConfig(**weather_data),
                logging=LoggingConfig(**logging_data),
            )
        except TypeError as e:
            raise ValueError(f"Invalid configuration in {path}: {e}") from e

    @classmethod
    def default(cls) -> "Config":
        """Create configuration with all defaults."""
        return cls()

    def to_toml_string(self) -> str:
        """Export configuration as TOML string."""
        lines = []
        lines.append("[device]")
        lines.append(f'mac_address = "{self.device.mac_address}"')
        lines.append(f'name = "{self.device.name}"')
        lines.append(f"rfcomm_port = {self.device.rfcomm_port}")
        lines.append("")
        lines.append("[weather]")
        lines.append(f"enabled = {str(self.weather.enabled).lower()}")
        lines.append(f"latitude = {self.weather.latitude}")
        lines.append(f"longitude = {self.weather.longitude}")
        lines.append(f"update_interval_minutes = {self.weather.update_interval_minutes}")
        lines.append(f'unit = "{self.weather.unit}"')
        lines.append("")
        lines.append("[logging]")
        lines.append(f'level = "{self.logging.level}"')
        lines.append(f'format = "{self.logging.format}"')
        return "\n".join(lines)


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration with fallback chain.

    Priority:
    1. Explicit path provided via argument
    2. ~/.config/ditoo/config.toml
    3. Default configuration
    """
    if config_path is not None:
        return Config.from_toml(config_path)

    default_path = Path.home() / ".config" / "ditoo" / "config.toml"
    if default_path.exists():
        return Config.from_toml(default_path)

    return Config.default()
