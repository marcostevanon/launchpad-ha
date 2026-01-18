import os
from dotenv import load_dotenv

# Load environment variables
try:
    load_dotenv()
except Exception:
    pass

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "/var/log/ha-launchpad.out.log")

# Home Assistant
HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1.5"))

HA_CONNECT_RETRY_DELAY = float(os.getenv("HA_CONNECT_RETRY_DELAY", "3.0"))
HA_CONNECT_MAX_DELAY = float(os.getenv("HA_CONNECT_MAX_DELAY", "30.0"))
HA_REQUEST_RETRY_DELAY = float(os.getenv("HA_REQUEST_RETRY_DELAY", "2.0"))
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
IDLE_TIMEOUT = int(os.getenv("LAUNCHPAD_IDLE_TIMEOUT", "1800")) # Default 30 minutes

LAUNCHPAD_ROTATION = int(os.getenv("LAUNCHPAD_ROTATION", "180"))

if LAUNCHPAD_ROTATION not in {0, 90, 180, 270}:
    raise ValueError("LAUNCHPAD_ROTATION must be 0, 90, 180 or 270")

# Disco Mode Settings
DISCO_LIGHTS = ["light.bulb_1", "light.bulb_2", "light.bulb_3"]
DISCO_SPEED = float(os.getenv("DISCO_SPEED", "0.5"))
