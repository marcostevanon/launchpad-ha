import logging
import time
from typing import Dict, Set, Optional, Any

from src.ha_launchpad.config.mapping import COLOR_PICK_ENABLED, BRIGHTNESS_ENABLED, IDLE_MODE_BUTTON_ID, RESTART_CHORD
from src.ha_launchpad.infrastructure.ha.client import HomeAssistantClient
from src.ha_launchpad.features.color_picker import ColorPicker
from src.ha_launchpad.features.disco import DiscoMode

logger = logging.getLogger(__name__)

class InputHandler:
    def __init__(
        self,
        ha_client: HomeAssistantClient,
        button_map: Dict[int, str],
        color_picker: ColorPicker,
        disco: DiscoMode
    ):
        self.ha_client = ha_client
        self.button_map = button_map
        self.color_picker = color_picker
        self.disco = disco
        self._palette_selected_notes: Set[int] = set()
        self._last_pressed_note: Optional[int] = None

    def handle_press(self, note: int, is_idle: bool = False) -> Dict[str, Any]:
        """
        Handle a button press. 
        Returns a dict of actions for the controller to perform.
        """
        
        # 1. Color Picker Delegation
        if self.color_picker.active and not is_idle:
            return self._handle_color_picker_input(note)
            
        # 1.5 Restart Chord Check
        if note == RESTART_CHORD[1] and self._last_pressed_note == RESTART_CHORD[0]:
             logger.warning("RESTART SEQUENCE DETECTED (%s->%s)", RESTART_CHORD[0], RESTART_CHORD[1])
             return {"restart": True}
        
        # Update last note
        self._last_pressed_note = note

        if is_idle:
            return {}

        # 2. Check mapping
        if note == IDLE_MODE_BUTTON_ID:
             return {"sleep": True}
             
        if note not in self.button_map:
            logger.warning("Unmapped button: %s", note)
            return {}
            
        entity_id = self.button_map[note]
        
        # 3. Special actions
        if entity_id == "disco_toggle":
            self.disco.toggle()
            return {"update_leds": True}
            
        if entity_id.startswith("volume_up."):
            self.ha_client.volume_up(entity_id.split(".", 1)[1])
            return {}
            
        if entity_id.startswith("volume_down."):
            self.ha_client.volume_down(entity_id.split(".", 1)[1])
            return {}
            
        if entity_id.startswith("plant."):
            return {}

        # 4. Standard Toggle
        return self._handle_toggle(note, entity_id)

    def _handle_color_picker_input(self, note: int):
        res = self.color_picker.handle_input(note)
        
        if res is None:
             return {} # Handled, but no action needed
             
        if res == -1:
             # Handled (ignored), stay in mode
             return {}

        # Dictionary result with selection info
        if isinstance(res, dict):
            source_note = res.get("source_note")
            pulse_color = res.get("pulse_color")
            
            if source_note:
                self._palette_selected_notes.add(source_note)
            
            if not self.color_picker.active:
                # Exiting mode -> Pulse and Update
                action = {"update_leds": True}
                if source_note and pulse_color:
                    action["pulse"] = {
                        "note": source_note, 
                        "color": pulse_color, 
                        "duration": 0.4,
                        "clear_note": note if note != source_note else None
                    }
                return action
                
        return {"update_leds": True}

    def _handle_toggle(self, note: int, entity_id: str):
        logger.info("Button %s pressed -> toggle %s", note, entity_id)
        
        # Optimistic feedback
        # We return a "flash" action that starts immediately
        # Then we perform the toggle. 
        # Ideally, toggle should be async or fast.
        
        success = self.ha_client.toggle_entity(entity_id)
        if success:
             return {
                 "update_leds": True,
                 "flash": {"note": note, "color": "yellow_3", "duration": 0.2}
             }
        return {}

    def handle_note_off(self, note: int):
        # Clean up selection logic
        if note in self._palette_selected_notes:
            self._palette_selected_notes.discard(note)
            return True # Suppress default behavior
        return False
