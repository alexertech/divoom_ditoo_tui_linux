"""CLI entry point for ditoo."""

import sys
import argparse
from pathlib import Path
from ditoo.ui import DitooApp
from ditoo.config import load_config
from ditoo.logging_setup import setup_logging


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Ditoo - Terminal controller for Divoom Ditoo-Plus",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config file (default: ~/.config/ditoo/config.toml)",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Override logging level",
    )

    parser.add_argument(
        "--generate-config",
        action="store_true",
        help="Generate example config file and exit",
    )

    parser.add_argument(
        "--mac",
        type=str,
        help="Override device MAC address",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    if args.generate_config:
        from ditoo.config import Config
        config = Config.default()
        print("# Ditoo Configuration File")
        print("# Save to: ~/.config/ditoo/config.toml")
        print()
        print(config.to_toml_string())
        sys.exit(0)

    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.log_level:
        config.logging.level = args.log_level
    if args.mac:
        config.device.mac_address = args.mac

    setup_logging(config.logging)

    try:
        app = DitooApp(config)
        app.run()
    except KeyboardInterrupt:
        print("\nDitoo controller stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
