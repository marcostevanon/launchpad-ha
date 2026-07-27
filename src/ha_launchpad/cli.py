#!/usr/bin/env python3
"""Thin entrypoint for Launchpad <-> Home Assistant controller"""

import logging
import time

from ha_launchpad.config.mapping import BUTTON_MAP
from ha_launchpad.config.settings import (
    HA_CONNECT_MAX_DELAY,
    HA_CONNECT_RETRY_DELAY,
    HA_TOKEN,
    HA_URL,
)
from ha_launchpad.core.controller import LaunchpadController
from ha_launchpad.infrastructure.ha.client import (
    HomeAssistantClient,
    HomeAssistantUnauthorized,
)
from ha_launchpad.infrastructure.midi.mido_backend import MidoBackend
from ha_launchpad.logging_config import configure_logging

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

    ha_client = HomeAssistantClient(HA_URL, HA_TOKEN)

    logger.info("Connecting to Home Assistant...")

    attempt = 0
    while True:
        attempt += 1
        try:
            if ha_client.is_available():
                logger.info("Connected")
                break
        except HomeAssistantUnauthorized as exc:
            logger.error("%s", exc)
            logger.error("Check HA_TOKEN in your .env - it is invalid or revoked.")
            raise SystemExit(1)
        logger.warning(
            "Failed to connect to Home Assistant. Check URL and token or wait for HA to become available."
        )

        # exponential backoff delay
        delay = min(HA_CONNECT_RETRY_DELAY * (2 ** (attempt - 1)), HA_CONNECT_MAX_DELAY)
        logger.info("Retrying in %.1fs...", delay)
        time.sleep(delay)

    backend = MidoBackend()
    # backend = MockBackend()
    controller = LaunchpadController(ha_client, BUTTON_MAP, backend=backend)
    controller.run()


if __name__ == "__main__":
    main()
