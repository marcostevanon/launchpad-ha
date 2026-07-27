import logging
import random
from typing import Any

from ha_launchpad.config.settings import DISCO_LIGHTS
from ha_launchpad.features.disco import DiscoMode
from ha_launchpad.infrastructure.ha.client import HomeAssistantClient
from ha_launchpad.infrastructure.midi.interface import MidiBackend

logger = logging.getLogger(__name__)

# Home Assistant states meaning "this device cannot be reached right now", as
# opposed to "it is switched off". Wi-Fi bulbs killed at a wall switch report
# `unavailable`, and rendering that as plain off hides the difference.
UNAVAILABLE_STATES = frozenset({"unavailable", "unknown"})
# The dimmest grey the device offers. An unreachable device is a passive fact,
# so its pad must sit *below* the "switched off" colour in brightness -- gray_2
# renders as a mid white and made offline bulbs the loudest thing on the board.
UNAVAILABLE_COLOR = "gray_1"


class LEDManager:
    def __init__(
        self,
        ha_client: HomeAssistantClient,
        backend: MidiBackend,
        button_map: dict[int, str],
        disco_mode: DiscoMode,
    ):
        self.ha_client = ha_client
        self.backend = backend
        self.button_map = button_map
        self.disco = disco_mode
        self._unknown_entities: set[str] = set()
        self._last_state: dict[int, str] = {}
        self._warned_no_states = False
        # Pads whose entity could not be reached at the last poll. Pressing one
        # cannot achieve anything, so the controller refuses to act on it.
        self._unavailable_notes: set[int] = set()

    def update_all(self, dry_run: bool = False) -> tuple[list, bool]:
        """
        Update all mapped LEDs based on HA states.

        Returns:
            (changes: list of (note, color, channel), has_notifications: bool)

        With dry_run the changes are reported but nothing is sent and nothing
        is recorded, leaving the caller free to decide what to display.
        """
        changes = []
        has_notifications = False
        current_state = {}

        # Fetch all states in one call
        all_states = self.ha_client.get_all_states()
        if not all_states:
            # The fetch failed. Leave the board showing the last known state
            # rather than repainting every pad as "unknown" over a blip. Report
            # once per outage, not once per poll.
            if not self._warned_no_states:
                logger.warning(
                    "No states returned from Home Assistant - LEDs left as-is"
                )
                self._warned_no_states = True
            return [], False

        self._warned_no_states = False
        state_map = {s["entity_id"]: s for s in all_states}

        for note, entity_id in self.button_map.items():
            if self.disco.active and entity_id in DISCO_LIGHTS:
                continue

            color, channel = self._determine_color(entity_id, state_map)

            # Track reachability regardless of dry_run: this is what Home
            # Assistant reports, not what is currently on the board.
            if color == UNAVAILABLE_COLOR:
                self._unavailable_notes.add(note)
            else:
                self._unavailable_notes.discard(note)

            # Check for notification condition (Plant problem = red pulse/color)
            if channel == 2 and "plant." in entity_id:
                # Plant problem is reported on the pulsing channel
                has_notifications = True

            # Create a simple representation of state: "color:channel"
            state_key = f"{color}:{channel}"
            current_state[note] = state_key

            # Check if changed
            if self._last_state.get(note) != state_key:
                changes.append((note, color, channel))
                if not dry_run:
                    self.backend.send_note(note, color, channel)

        # Only bank the new state once it has actually been sent to the board.
        # A dry run reports what changed without emitting, so recording it here
        # would leave the cache claiming pads are lit that were never painted.
        if not dry_run:
            self._last_state = current_state

        return changes, has_notifications

    def is_unavailable(self, note: int) -> bool:
        """Whether this pad's entity was unreachable at the last poll."""
        return note in self._unavailable_notes

    def commit(self, changes) -> None:
        """Record changes as already displayed, so they are not reported again.

        Used when something other than update_all() has put these colours on
        the board -- the standby preview, which paints a sleeping board itself.
        """
        for note, color, channel in changes:
            self._last_state[note] = f"{color}:{channel}"

    def invalidate_cache(self):
        """Force next update to resend all states."""
        self._last_state = {}

    def _determine_color(self, entity_id: str, state_map: dict[str, Any]):
        """Determine the color and channel for a given entity."""
        # Special cases
        if entity_id == "disco_toggle":
            if self.disco.active:
                colors = ["orange_1", "green_1", "cyan_1", "pink_2", "yellow_1"]
                return random.choice(colors), 2
            return "orange_1", 0

        # Manual Sleep Button (always orange_3 when active)
        if entity_id == "manual_sleep":
            return "lightblue_0", 0

        if entity_id.startswith(("volume_up.", "volume_down.")):
            return self._get_volume_button_color(entity_id, state_map)

        # Standard entities
        state_data = state_map.get(entity_id)
        if not state_data:
            return "red_2", 0  # Default/Unknown

        state = state_data.get("state", "unknown")
        domain = entity_id.split(".")[0]

        # Offline is not the same as off, and should not look like it.
        if state in UNAVAILABLE_STATES:
            return UNAVAILABLE_COLOR, 0

        if domain in ["light", "switch"]:
            if state == "on":
                if domain == "light" and "attributes" in state_data:
                    return self._get_dimmed_color(state_data["attributes"]), 0
                return "green_1", 0
            return "amber_1", 0

        if domain == "scene":
            return "blue_1", 0

        if domain == "script":
            return "purple_1", 0

        if domain == "media_player":
            if state == "playing":
                return "cyan_0", 2
            if state == "paused":
                return "amber_1", 0
            return "amber_1", 0

        if domain == "plant":
            problem = state_data.get("attributes", {}).get("problem", "unknown")
            if problem == "none":
                return "green_3", 0
            return "red_2", 2

        # Unknown domain
        self._unknown_entities.add(entity_id)
        return "red_2", 0

    def _get_volume_button_color(self, entity_id: str, state_map: dict[str, Any]):
        """Colour a volume pad after the player it controls."""
        target = entity_id.split(".", 1)[1]
        state_data = state_map.get(target)

        if not state_data or state_data.get("state") in UNAVAILABLE_STATES:
            return UNAVAILABLE_COLOR, 0

        # The pad can only do something if the player reports a level to
        # adjust. A TV that is off has no volume_level, so the service call
        # would just fail -- show that rather than a lit, dead pad.
        if state_data.get("attributes", {}).get("volume_level") is None:
            return UNAVAILABLE_COLOR, 0

        return "purple_1", 0

    def _get_dimmed_color(self, attributes: dict):
        brightness = attributes.get("brightness", 255)
        if brightness <= 85:
            return "green_3"
        if brightness <= 170:
            return "green_2"
        return "green_1"
