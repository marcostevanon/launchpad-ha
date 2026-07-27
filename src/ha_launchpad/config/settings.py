import os

from dotenv import load_dotenv

# Load environment variables. HA_ENV_FILE lets the secrets live outside the
# deployed code, so releases can be replaced without touching the token and the
# token never sits inside a git tree.
try:
    _env_file = os.getenv("HA_ENV_FILE")
    load_dotenv(_env_file) if _env_file else load_dotenv()
except Exception:
    pass

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
# Default to somewhere a user agent can actually write. The old default,
# /var/log, is root-only, and the failure was swallowed silently.
LOG_FILE = os.getenv(
    "LOG_FILE",
    os.path.expanduser("~/Library/Logs/com.launchpad.ha/app.log"),
)
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024)))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# Home Assistant
HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1.5"))

HA_CONNECT_RETRY_DELAY = float(os.getenv("HA_CONNECT_RETRY_DELAY", "3.0"))
HA_CONNECT_MAX_DELAY = float(os.getenv("HA_CONNECT_MAX_DELAY", "30.0"))
# Ceiling for urllib3's per-request backoff. The growth curve itself is owned
# by the retry policy in the HA client, so there is no separate initial delay.
HA_REQUEST_MAX_DELAY = float(os.getenv("HA_REQUEST_MAX_DELAY", "5.0"))

# Volume
VOLUME_STEP = float(os.getenv("VOLUME_STEP", "0.07"))

# Launchpad Connection
LAUNCHPAD_VENDOR = int(os.getenv("LAUNCHPAD_VENDOR", "0x1235"), 16)
LAUNCHPAD_PRODUCT = int(os.getenv("LAUNCHPAD_PRODUCT", "0x0113"), 16)
LAUNCHPAD_IDENT = os.getenv("LAUNCHPAD_IDENT", "LPMiniMK3 MIDI")
LAUNCHPAD_INACTIVITY_TIMEOUT = float(os.getenv("LAUNCHPAD_INACTIVITY_TIMEOUT", "15.0"))

LAUNCHPAD_ALIVE_DELAY = float(os.getenv("LAUNCHPAD_ALIVE_DELAY", "3.0"))
LAUNCHPAD_RETRY_DELAY = float(os.getenv("LAUNCHPAD_RETRY_DELAY", "5.0"))
LAUNCHPAD_MAX_RETRY_DELAY = float(os.getenv("LAUNCHPAD_MAX_RETRY_DELAY", "10.0"))

# Idle Mode
IDLE_TIMEOUT = int(os.getenv("LAUNCHPAD_IDLE_TIMEOUT", "1800"))  # Default 30 minutes
# How often to check Home Assistant while asleep. This also sets how quickly a
# change elsewhere in the house shows up as a standby preview.
IDLE_POLL_INTERVAL = float(os.getenv("LAUNCHPAD_IDLE_POLL_INTERVAL", "10.0"))
# How long a pad stays lit on the sleeping board after its entity changed.
STANDBY_PREVIEW_DURATION = float(
    os.getenv("LAUNCHPAD_STANDBY_PREVIEW_DURATION", "120.0")
)

# Deployment identity and liveness. The deploy script waits for the heartbeat
# to carry the new release id before it considers a release healthy; `launchctl
# print` cannot tell it whether Home Assistant and the Launchpad are actually up.
RELEASE_ID = os.getenv("LAUNCHPAD_RELEASE_ID", "dev")
HEARTBEAT_FILE = os.getenv("LAUNCHPAD_HEARTBEAT_FILE", "")
HEARTBEAT_INTERVAL = float(os.getenv("LAUNCHPAD_HEARTBEAT_INTERVAL", "5.0"))

LAUNCHPAD_ROTATION = int(os.getenv("LAUNCHPAD_ROTATION", "180"))

if LAUNCHPAD_ROTATION not in {0, 90, 180, 270}:
    raise ValueError("LAUNCHPAD_ROTATION must be 0, 90, 180 or 270")

# Disco Mode Settings
DISCO_LIGHTS = ["light.bulb_1", "light.bulb_2", "light.bulb_3"]
DISCO_SPEED = float(os.getenv("DISCO_SPEED", "2.0"))
# Crossfade length, in WHOLE seconds. The Trådfri integration does
# `int(transition) * 10` to convert to deciseconds, so any value below 1.0
# truncates to zero and the colour changes instantly instead of fading.
DISCO_TRANSITION = int(os.getenv("DISCO_TRANSITION", "2"))
# Applied once when disco starts, never per step -- see disco.py.
DISCO_BRIGHTNESS = int(os.getenv("DISCO_BRIGHTNESS", "254"))
