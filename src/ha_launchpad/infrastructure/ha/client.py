"""Home Assistant API wrapper used by the Launchpad controller."""

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ha_launchpad.config.settings import (
    HA_REQUEST_MAX_DELAY,
    VOLUME_STEP,
)

logger = logging.getLogger(__name__)

# (connect, read) timeouts. The read budget for polling has to fit inside the
# poll interval, otherwise one slow response stalls every LED update behind it.
POLL_TIMEOUT = (2.0, 3.0)
# Service calls block until Home Assistant has finished running them, which for
# a cloud-backed light or a speaker is legitimately slow.
SERVICE_TIMEOUT = (2.0, 10.0)

# Transient server-side conditions; a restarting Home Assistant behind a proxy
# typically shows up as 502/503.
RETRYABLE_STATUSES = (408, 429, 500, 502, 503, 504)


class HomeAssistantUnauthorized(Exception):
    """The token was rejected. No amount of retrying will fix it."""


class HomeAssistantClient:
    def __init__(self, url: str, token: str):
        self.url = url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }
        )

        retry = Retry(
            total=2,
            connect=2,
            read=2,
            status=2,
            backoff_factor=0.3,
            backoff_max=HA_REQUEST_MAX_DELAY,
            backoff_jitter=0.2,
            status_forcelist=RETRYABLE_STATUSES,
            # Read and status retries are gated by method. A POST that timed
            # out on read may well have run the service already, and replaying
            # `light.toggle` would flip the light straight back. Connect
            # failures are not gated, because there the request provably never
            # reached Home Assistant.
            allowed_methods=frozenset(["GET"]),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=2, pool_maxsize=4)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Whether we are currently in an outage, so a Home Assistant restart
        # reports once rather than on every poll for as long as it lasts.
        self._offline = False

    def _report_unreachable(self, method: str, endpoint: str, error) -> None:
        if self._offline:
            logger.debug("Still unreachable (%s %s): %s", method, endpoint, error)
            return

        logger.warning("Home Assistant unreachable (%s %s): %s", method, endpoint, error)
        self._offline = True

    def _report_reachable(self) -> None:
        if self._offline:
            logger.info("Home Assistant reachable again")
            self._offline = False

    def _request(
        self, method: str, endpoint: str, *, timeout, **kwargs
    ) -> requests.Response | None:
        """Perform one logical request.

        Transport-level retries and backoff are handled inside urllib3, so this
        always terminates. Returns None when the request could not be
        completed; raises only when the failure is not worth retrying at all.
        """
        try:
            resp = self.session.request(
                method, endpoint, timeout=timeout, **kwargs
            )
        except requests.exceptions.RequestException as e:
            self._report_unreachable(method, endpoint, e)
            return None

        self._report_reachable()

        if resp.status_code == 401:
            # Retrying a rejected token achieves nothing and, if Home Assistant
            # has IP banning enabled, will eventually lock this host out.
            raise HomeAssistantUnauthorized(
                f"Home Assistant rejected the access token: {resp.text[:200]}"
            )

        if resp.status_code == 404:
            logger.debug("Not found (404): %s", endpoint)
            return None

        if resp.status_code >= 400:
            logger.error(
                "Home Assistant returned %s for %s %s: %s",
                resp.status_code,
                method,
                endpoint,
                resp.text[:200],
            )
            return None

        return resp

    def call_service(self, domain: str, service: str, entity_id: str, **kwargs) -> bool:
        """Call a Home Assistant service"""
        endpoint = f"{self.url}/api/services/{domain}/{service}"
        data = {"entity_id": entity_id, **kwargs}

        resp = self._request("POST", endpoint, timeout=SERVICE_TIMEOUT, json=data)
        if resp is None:
            logger.error(
                "Error calling service %s.%s for %s", domain, service, entity_id
            )
            return False

        logger.info("Called %s.%s for %s", domain, service, entity_id)
        return True

    def is_available(self) -> bool:
        """Report whether the API answers and accepts our token.

        `GET /api/` is Home Assistant's own health endpoint, so unlike probing
        an entity this does not depend on anything in particular existing.
        """
        resp = self._request("GET", f"{self.url}/api/", timeout=POLL_TIMEOUT)
        if resp is None:
            return False

        try:
            return resp.json().get("message") == "API running."
        except ValueError:
            logger.error("Invalid JSON response from /api/")
            return False

    def get_all_states(self) -> list[dict[str, Any]]:
        """Fetch all entity states from Home Assistant in one call.

        Returns an empty list if the states could not be fetched, which callers
        must treat as "unknown" rather than "nothing is on".
        """
        endpoint = f"{self.url}/api/states"
        resp = self._request("GET", endpoint, timeout=POLL_TIMEOUT)
        if resp is None:
            return []

        try:
            return resp.json()
        except ValueError:
            logger.error("Invalid JSON response from /api/states")
            return []

    def get_state(self, entity_id: str) -> dict[str, Any]:
        """Get the state of an entity. Returns 'not_found' if entity doesn't exist."""
        endpoint = f"{self.url}/api/states/{entity_id}"
        resp = self._request("GET", endpoint, timeout=POLL_TIMEOUT)
        if resp is None:
            return {"error": "not_found"}

        try:
            return resp.json()
        except ValueError:
            logger.error("Invalid JSON response for %s", entity_id)
            return {}

    def toggle_entity(self, entity_id: str) -> bool:
        """Trigger action based on entity domain."""
        domain = entity_id.split(".")[0]

        if domain == "light":
            return self.call_service("light", "toggle", entity_id)
        elif domain == "switch":
            return self.call_service("switch", "toggle", entity_id)
        elif domain == "scene":
            return self.call_service("scene", "turn_on", entity_id)
        elif domain == "script":
            return self.call_service("script", "turn_on", entity_id)
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
