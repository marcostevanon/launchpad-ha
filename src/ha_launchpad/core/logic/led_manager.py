import logging
import random
from typing import Dict, Set

from src.ha_launchpad.config.settings import DISCO_LIGHTS
from src.ha_launchpad.infrastructure.midi.interface import MidiBackend
from src.ha_launchpad.infrastructure.ha.client import HomeAssistantClient
from src.ha_launchpad.features.disco import DiscoMode

logger = logging.getLogger(__name__)

class LEDManager:
    def __init__(
        self, 
        ha_client: HomeAssistantClient, 
        backend: MidiBackend,
        button_map: Dict[int, str],
        disco_mode: DiscoMode
    ):
        self.ha_client = ha_client
        self.backend = backend
        self.button_map = button_map
        self.disco = disco_mode
        self._unknown_entities: Set[str] = set()

    def update_all(self):
        """Update all mapped LEDs based on HA states"""
        for note, entity_id in self.button_map.items():
            if self.disco.active and entity_id in DISCO_LIGHTS:
                continue

            color, channel = self._determine_color(entity_id)
            self.backend.send_note(note, color, channel)

    def _determine_color(self, entity_id: str):
        """Determine the color and channel for a given entity."""
        # Special cases
        if entity_id == "disco_toggle":
            if self.disco.active:
                colors = ["orange_1", "green_1", "cyan_1", "pink_2", "yellow_1"]
                return random.choice(colors), 2
            return "orange_1", 0
        
        if entity_id.startswith("volume_up.") or entity_id.startswith("volume_down."):
            return self._get_volume_button_color(entity_id)

        # Standard entities
        state_data = self.ha_client.get_state(entity_id)
        if not state_data:
            return "red_2", 0 # Default/Unknown

        state = state_data.get("state", "unknown")
        domain = entity_id.split(".")[0]
        
        if domain in ["light", "switch"]:
            if state == "on":
                if domain == "light" and "attributes" in state_data:
                    return self._get_dimmed_color(state_data["attributes"]), 0
                return "green_1", 0
            return "amber_1", 0
            
        if domain == "scene":
            return "blue_1", 0
            
        if domain == "media_player":
            if state == "playing":
                return "cyan_0", 2
            if state == "paused":
                return "amber_1", 0
            if "nestmini" in entity_id or "studio_speaker" in entity_id:
                return "off", 0
            return "amber_1", 0
            
        if domain == "plant":
            problem = state_data.get("attributes", {}).get("problem", "unknown")
            if problem == "none":
                return "green_3", 0
            return "red_2", 2

        # Unknown domain
        self._unknown_entities.add(entity_id)
        return "red_2", 0

    def _get_volume_button_color(self, entity_id: str):
        target = entity_id.split(".", 1)[1]
        if "nestmini" in target or "studio_speaker" in target:
            state = self.ha_client.get_state(target)
            if state and state.get("state") in ["playing", "paused"]:
                return "purple_1", 0
            return "off", 0
        return "purple_1", 0
    
    def _get_dimmed_color(self, attributes: Dict):
        brightness = attributes.get("brightness", 255)
        if brightness <= 85:
            return "green_3"
        if brightness <= 170:
            return "green_2"
        return "green_1"
