# Launchpad HA Controller

A utility that connects a Novation Launchpad to Home Assistant. Button presses toggle Home Assistant entities, and Home Assistant states are reflected on the Launchpad LEDs.

## Features

- Bidirectional control: Launchpad buttons control Home Assistant entities, and entity states update Launchpad LEDs
- Configurable button mapping to any Home Assistant entity (lights, switches, scenes, media players)
- Color picker mode for RGB lights
- Disco mode for automated light shows on configured spotlights
- Launchpad rotation support (0°, 90°, 180°, 270°)
- Automatic reconnection to Launchpad and Home Assistant

## Prerequisites (macOS)

- Python 3.11 or later
- Homebrew
- Novation Launchpad (Mini MK3 tested)

Install system dependencies:

```bash
brew install python@3.11 rtmidi
```

## Configuration

Create a `.env` file in the project root (see `.env.example` for all options):

```env
HA_URL=http://your-home-assistant:8123
HA_TOKEN=your_long_lived_home_assistant_token_here
```

- `HA_URL`: URL of your Home Assistant instance
- `HA_TOKEN`: Long-lived access token from Home Assistant (Settings > Devices & Services > Helpers > Long-lived access tokens)

The button mapping is configured in `src/ha_launchpad/config.py`. Edit the `BUTTON_MAP` dictionary to map Launchpad pad numbers to Home Assistant entity IDs.

## Installation

Run the installation script:

```bash
./install.sh
```

This will:
- Create a virtual environment in `~/.local/launchpad-ha/venv/`
- Install Python dependencies
- Copy the project files
- Install a user LaunchAgent for automatic startup
- Set up logging to `/tmp/ha-launchpad.out.log` and `/tmp/ha-launchpad.err.log`

## Usage

After installation, the service starts automatically. The Launchpad LEDs will reflect the current state of mapped entities.

- Press buttons to toggle entities
- Hold buttons in `COLOR_PICK_ENABLED` to enter color picker mode
- The controller polls Home Assistant every second for state updates

To run manually for testing:

```bash
source venv/bin/activate
python -m src.ha_launchpad.cli
```

## Project Structure

- `src/ha_launchpad/` — Main package
  - `api.py` — Home Assistant HTTP API wrapper
  - `controller.py` — Launchpad controller logic and MIDI handling
  - `config.py` — Configuration loading from environment and constants
  - `cli.py` — Command-line entry point
  - `logging_config.py` — Logging setup
  - `backend/` — MIDI backend implementations
    - `mido_backend.py` — Production backend using `mido` + `python-rtmidi`
    - `mock_backend.py` — Mock backend for testing
  - `utils/` — Utilities
    - `rotate_pad.py` — Pad rotation logic
- `requirements.txt` — Python dependencies
- `pyproject.toml` — Package metadata and console script
- `packaging/com.launchpad.ha.plist` — macOS LaunchAgent template
- `install.sh` — macOS installation script
- `.env.example` — Example environment configuration

## Logging

Logs include timestamp, level, logger name, filename, and line number.

- Standard output: `/tmp/ha-launchpad.out.log`
- Standard error: `/tmp/ha-launchpad.err.log`

View logs:

```bash
tail -f /tmp/ha-launchpad.out.log
tail -f /tmp/ha-launchpad.err.log
```

Set `LOG_LEVEL=DEBUG` in `.env` for verbose logging.

## Why `mido` + `python-rtmidi`?

- `mido`: High-level Python MIDI library with convenient message objects and API
- `python-rtmidi`: Backend that binds to the native RtMidi C++ library for hardware access on macOS


## Future Plans

See `TODO.md` for planned features like sleep mode, volume controls, and error notifications.
