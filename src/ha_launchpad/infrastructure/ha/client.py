"""Home Assistant API wrapper used by the Launchpad controller."""

from typing import Dict, Any, Optional
import time
import requests
import logging

from src.ha_launchpad.config.settings import (
    HA_REQUEST_RETRY_DELAY,
    HA_REQUEST_MAX_DELAY,
    VOLUME_STEP,
)

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    def __init__(self, url: str, token: str):
        self.url = url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self.session = requests.Session()

    def _request_with_retry(
        self, method: str, endpoint: str, **kwargs
    ) -> Optional[requests.Response]:
        """Perform an HTTP request with retry/backoff."""
        delay = HA_REQUEST_RETRY_DELAY

        while True:
            try:
                resp = self.session.request(
                    method, endpoint, headers=self.headers, timeout=5, **kwargs
                )
                resp.raise_for_status()
                return resp
            except requests.exceptions.HTTPError as e:
                # Don't retry 404s - entity doesn't exist
                if e.response.status_code == 404:
                    logger.debug("Entity not found (404). Error: %s", e)
                    return None
            except requests.exceptions.RequestException as e:
                logger.warning(
                    "Connection to Home Assistant failed. Retrying... Error: %s", e
                )
                time.sleep(min(delay, HA_REQUEST_MAX_DELAY))
                delay = min(delay * 2, HA_REQUEST_MAX_DELAY)
                continue

    def call_service(self, domain: str, service: str, entity_id: str, **kwargs) -> bool:
        """Call a Home Assistant service"""
        endpoint = f"{self.url}/api/services/{domain}/{service}"
        data = {"entity_id": entity_id, **kwargs}

        resp = self._request_with_retry("POST", endpoint, json=data)
        if resp is None:
            logger.error(
                "Error calling service %s.%s for %s", domain, service, entity_id
            )
            return False

        logger.info("Called %s.%s for %s", domain, service, entity_id)
        return True

    def get_state(self, entity_id: str) -> Dict[str, Any]:
        """Get the state of an entity. Returns 'not_found' if entity doesn't exist."""
        endpoint = f"{self.url}/api/states/{entity_id}"
        resp = self._request_with_retry("GET", endpoint)
        if resp is None:
            return {"error": "not_found"}

        try:
            return resp.json()
        except ValueError:
            logger.error("Invalid JSON response for %s", entity_id)
            return {}

    def toggle_entity(self, entity_id: str) -> bool:
        """Toggle a light, switch or activate a scene."""
        domain = entity_id.split(".")[0]

        if domain == "light":
            return self.call_service("light", "toggle", entity_id)
        elif domain == "switch":
            return self.call_service("switch", "toggle", entity_id)
        elif domain == "scene":
            return self.call_service("scene", "turn_on", entity_id)
        elif domain == "media_player":
            state_data = self.get_state(entity_id)
            if state_data and state_data.get("state") in ["off", "unavailable"]:
                logger.debug("Media player %s is %s - skipping play/pause command", entity_id, state_data.get("state"))
                return True
            # For all media players, use play/pause toggle when active
            return self.call_service("media_player", "media_play_pause", entity_id)
        else:
            logger.error("Unknown domain: %s", domain)
            return False

    def volume_up(self, entity_id: str) -> bool:
        """Increase volume of a media player by VOLUME_STEP."""
        return self._adjust_volume(entity_id, VOLUME_STEP)

    def volume_down(self, entity_id: str) -> bool:
        """Decrease volume of a media player by VOLUME_STEP."""
        return self._adjust_volume(entity_id, -VOLUME_STEP)

    def _adjust_volume(self, entity_id: str, delta: float) -> bool:
        """Adjust volume by delta, clamped to 0.0-1.0."""
        state = self.get_state(entity_id)
        if "error" in state:
            logger.error("Cannot get state for volume adjustment: %s", entity_id)
            return False

        current_volume = state.get("attributes", {}).get("volume_level")
        if current_volume is None:
            logger.error("Volume level not available for %s", entity_id)
            return False

        new_volume = max(0.0, min(1.0, current_volume + delta))
        return self.call_service("media_player", "volume_set", entity_id, volume_level=new_volume)
