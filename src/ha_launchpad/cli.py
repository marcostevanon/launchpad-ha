#!/usr/bin/env python3
"""Thin entrypoint for Launchpad <-> Home Assistant controller"""

import time
import logging

from .config import (
    HA_URL,
    HA_TOKEN,
    BUTTON_MAP,
    HA_CONNECT_RETRY_DELAY,
    HA_CONNECT_MAX_DELAY,
)
from .backend.mido_backend import MidoBackend
from .backend.mock_backend import MockBackend
from .api import HomeAssistantAPI
from .controller import LaunchpadController
from .logging_config import configure_logging


logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging()

    if not HA_URL:
        logger.error(
            "ERROR: HA_URL is not set.\nSet it in your shell or create a .env file with 'HA_URL=http://your-home-assistant:8123'."
        )
        raise SystemExit(1)

    if not HA_TOKEN:
        logger.error(
            "ERROR: HA_TOKEN is not set.\nSet it in your shell or create a .env file with 'HA_TOKEN=your_long_lived_home_assistant_token'."
        )
        raise SystemExit(1)

    ha_api = HomeAssistantAPI(HA_URL, HA_TOKEN)

    logger.info("Connecting to Home Assistant...")

    attempt = 0
    while True:
        attempt += 1
        test_state = ha_api.get_state("sun.sun")
        if test_state:
            logger.info("Connected")
            break
        logger.warning(
            "Failed to connect to Home Assistant. Check URL and token or wait for HA to become available."
        )

        # exponential backoff delay
        delay = min(HA_CONNECT_RETRY_DELAY * (2 ** (attempt - 1)), HA_CONNECT_MAX_DELAY)
        logger.info("Retrying in %.1fs...", delay)
        time.sleep(delay)

    backend = MidoBackend()
    # backend = MockBackend()
    controller = LaunchpadController(ha_api, BUTTON_MAP, backend=backend)
    controller.run()


if __name__ == "__main__":
    main()
