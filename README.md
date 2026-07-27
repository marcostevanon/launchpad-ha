# Launchpad HA Controller

A utility that connects a Novation Launchpad to Home Assistant. Button presses toggle Home Assistant entities, and Home Assistant states are reflected on the Launchpad LEDs.

## Features

- Bidirectional control: Launchpad buttons control Home Assistant entities, and entity states update Launchpad LEDs
- Configurable button mapping to any Home Assistant entity (lights, switches, scenes, scripts, media players, plants)
- Colour picker and brightness picker, entered by holding a light's pad
- Disco mode for automated light shows on configured spotlights
- Standby mode: the board sleeps after inactivity, and changes made elsewhere in the house light the affected pads for a couple of minutes without waking it
- Launchpad rotation support (0°, 90°, 180°, 270°)
- Automatic reconnection to the Launchpad and to Home Assistant

## Prerequisites (macOS)

- [uv](https://docs.astral.sh/uv/) — manages both the Python interpreter and the dependencies
- Novation Launchpad (Mini MK3 tested)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

You do **not** need to install Python yourself: `uv` provisions the version pinned in `.python-version`.

## Configuration

Copy `.env.example` to `.env` and fill in at least:

```env
HA_URL=http://your-home-assistant:8123
HA_TOKEN=your_long_lived_home_assistant_token_here
```

Create the token in Home Assistant under your profile → Security → Long-lived access tokens.

Everything else in `.env.example` is optional and documented inline. The button mapping lives in [`src/ha_launchpad/config/mapping.py`](src/ha_launchpad/config/mapping.py) — edit `BUTTON_MAP` to map pad numbers to entities.

Pads are numbered `row * 10 + column`, with row 1 at the bottom left, so the 8×8 grid runs 11–88.

## Development

```bash
uv sync              # create .venv and install everything
uv run pytest        # run the tests
uv run ruff check    # lint
uv run ruff format   # format
```

To work against a Launchpad plugged into your development machine:

```bash
./scripts/dev.sh
```

This runs the controller, streams logs to the terminal, and restarts it automatically every time you commit, so each change can be checked on the hardware. Ctrl-C stops it.

To check the hardware on its own:

```bash
uv run python check_hardware.py
```

## Deployment

The service runs on an always-on Mac as a user LaunchAgent. It must be an *agent* rather than a daemon: CoreMIDI is only reachable from the per-user GUI bootstrap namespace.

One-time setup on the target machine — install `uv`, then create the secrets file outside the deploy path:

```bash
mkdir -p ~/.local/launchpad-ha/shared
cp .env.example ~/.local/launchpad-ha/shared/env   # then fill in HA_URL and HA_TOKEN
chmod 600 ~/.local/launchpad-ha/shared/env
```

Then, from your development machine:

```bash
./scripts/deploy.sh macmini
```

Each deploy creates an immutable release with its own virtualenv, builds and self-tests it while the running version is still serving, and only then swaps a `current` symlink in a single atomic rename:

```
~/.local/launchpad-ha/
├── releases/20260727T183000-a1b2c3d/   code + .venv, immutable
├── shared/env                          secrets, 0600, never touched by a deploy
├── bin/run                             stable path the plist points at
└── current -> releases/...
```

Health is judged on the application's heartbeat file carrying the new release id — proof it reached Home Assistant and opened the Launchpad, which `launchctl print` cannot tell you. If it does not become healthy, the symlink flips back to the previous release and the deploy exits non-zero.

To roll back by hand, point `current` at an older release and restart:

```bash
ssh macmini
cd ~/.local/launchpad-ha
ln -s releases/<older> current.tmp && mv -h current.tmp current
launchctl kickstart -k gui/$(id -u)/com.launchpad.ha
```

Only tracked files are shipped, so `.git`, `.venv` and `.env` never reach the server.

## Project structure

- `src/ha_launchpad/`
  - `cli.py` — entry point (`ha-launchpad`), also `--selftest`
  - `config/` — `settings.py` (environment) and `mapping.py` (pads, colours, palettes)
  - `core/controller.py` — orchestration, threads, MIDI event loop
  - `core/logic/` — LED manager, input handler, feedback, idle/standby
  - `features/` — colour picker, disco mode
  - `infrastructure/midi/` — `MidiBackend` interface, mido backend, rotation decorator, mock backend
  - `infrastructure/ha/` — Home Assistant HTTP client
  - `utils/rotate_pad.py` — pad rotation maths
- `scripts/dev.sh` — local run loop, restarts on every commit
- `scripts/deploy.sh` — atomic versioned deploy
- `packaging/` — LaunchAgent plist template and the `bin/run` wrapper
- `tests/` — unit and integration tests

## Logging

Logs go to `~/Library/Logs/com.launchpad.ha/app.log` and rotate in-process (5 MB, 5 backups). Rotation has to happen in-process: launchd opens its redirect targets once at spawn and never reopens them, so an external rotator would leave the service writing to a deleted file.

```bash
tail -f ~/Library/Logs/com.launchpad.ha/app.log
```

`launchd.out.log` and `launchd.err.log` in the same directory catch anything that never reaches the logger, such as import errors and interpreter crashes.

Set `LOG_LEVEL=DEBUG` for verbose output, or `LOG_FILE=` (empty) to log to stderr instead.

## Why `mido` + `python-rtmidi`?

- `mido`: high-level MIDI library with convenient message objects
- `python-rtmidi`: binds the native RtMidi C++ library for hardware access on macOS

The Launchpad is put into Programmer Mode at startup and handed back to Live Mode on shutdown — Programmer Mode disables the device's own Setup menu, so leaving it there would require a power cycle to undo.

## Future plans

See [`TODO.md`](TODO.md).
