#!/usr/bin/env python3
"""Thin entrypoint for Launchpad <-> Home Assistant controller"""

import argparse
import logging
import time

from ha_launchpad.config.mapping import BUTTON_MAP
from ha_launchpad.config.settings import (
    HA_CONNECT_MAX_DELAY,
    HA_CONNECT_RETRY_DELAY,
    HA_TOKEN,
    HA_URL,
    RELEASE_ID,
)
from ha_launchpad.core.controller import LaunchpadController
from ha_launchpad.infrastructure.ha.client import (
    HomeAssistantClient,
    HomeAssistantUnauthorized,
)
from ha_launchpad.infrastructure.midi.mido_backend import MidoBackend
from ha_launchpad.logging_config import configure_logging

logger = logging.getLogger(__name__)


def selftest() -> int:
    """Check this build can actually run, without touching the hardware.

    A deploy runs this inside the new release while the live one is still
    serving, so a bad config, an unimportable module or a dead token fails
    before anything is switched over.
    """
    logger.info("Self-test: release %s", RELEASE_ID)

    if not HA_URL or not HA_TOKEN:
        logger.error("Self-test failed: HA_URL and HA_TOKEN must both be set")
        return 1

    # Importing the mapping validates the pad tables; settings validates
    # LAUNCHPAD_ROTATION at import time.
    logger.info("Self-test: %d pads mapped", len(BUTTON_MAP))

    try:
        if not HomeAssistantClient(HA_URL, HA_TOKEN).is_available():
            logger.error(
                "Self-test failed: Home Assistant did not answer at %s", HA_URL
            )
            return 1
    except HomeAssistantUnauthorized as exc:
        logger.error("Self-test failed: %s", exc)
        return 1

    logger.info("Self-test passed")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="ha-launchpad", description=__doc__)
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="validate configuration and Home Assistant connectivity, then exit",
    )
    args = parser.parse_args()

    configure_logging()

    if args.selftest:
        raise SystemExit(selftest())

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
