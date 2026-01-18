import logging
from typing import Optional, Set

from src.ha_launchpad.config.mapping import COLOR_PALETTE, BRIGHTNESS_PALETTE

logger = logging.getLogger(__name__)

class ColorPicker:
    def __init__(self, ha_client, midi_backend):
        self.ha_client = ha_client
        self.backend = midi_backend
        self.active = False
        self.target_entity: Optional[str] = None
        self.source_note: Optional[int] = None
        self.selected_notes: Set[int] = set()

    def enter(self, entity_id: str, source_note: int, show_colors: bool = True, show_brightness: bool = True):
        """Enter adjustment mode for a target entity and show the palettes."""
        self.active = True
        self.target_entity = entity_id
        self.source_note = source_note
        self.selected_notes.discard(source_note)

        # Visual feedback: mark the source pad
        try:
            if self.backend and self.backend.is_connected():
                self.backend.send_note(self.source_note, "yellow_3", channel=2)
                
                # Show color palette if enabled
                if show_colors:
                    for note, info in COLOR_PALETTE.items():
                        self.backend.send_note(note, info["color"])
                
                # Show brightness palette if enabled
                if show_brightness:
                    for note in BRIGHTNESS_PALETTE.keys():
                        self.backend.send_note(note, "yellow_3")
        except Exception as e:
            logger.warning("Error entering color pick mode: %s", e)

    def exit(self):
        """Exit color pick mode."""
        self.active = False
        self.target_entity = None
        self.source_note = None

        # Turn off palettes
        if self.backend and self.backend.is_connected():
            # Clear color palette
            for note in COLOR_PALETTE.keys():
                try:
                    self.backend.send_note(note, "off")
                except Exception:
                    pass
            # Clear brightness palette
            for note in BRIGHTNESS_PALETTE.keys():
                try:
                    self.backend.send_note(note, "off")
                except Exception:
                    pass

    def handle_input(self, note: int) -> Optional[int]:
        """
        Handle input while in color pick mode.
        Returns the source_note if a palette color was picked, 
        otherwise returns None if the input was handled (consumed), 
        and raises an exception/returns specific value if not handled? 
        Actually, let's stick to returning source_note if 'consumed and selected',
        True if 'consumed but not selected', and False if 'not handled'.
        Wait, let's keep it simple: return the source_note and a flag.
        
        Better: return True if handled, and modify a state to indicate selection.
        """
        if not self.active:
            return None

        # If press is on the source pad
        if note == self.source_note:
            if not self.selected_notes and self.target_entity:
                # Short-tap while palette shown -> toggle the entity (backward compatibility)
                logger.info(
                    "Source pad released without palette selection -> toggling %s",
                    self.target_entity,
                )
                try:
                    self.ha_client.toggle_entity(self.target_entity)
                except Exception:
                    pass
            self.exit()
            return None # Not a "selection" that suppresses future off-handling

        # If press is on palette -> pick color
        if note in COLOR_PALETTE and self.target_entity:
            r, g, b = COLOR_PALETTE[note]["rgb"]
            logger.info("Picked color %s for %s", (r, g, b), self.target_entity)
            
            # Send to Home Assistant
            try:
                self.ha_client.call_service(
                    "light", "turn_on", self.target_entity, rgb_color=[r, g, b]
                )
            except Exception:
                pass
            
            consumed_source_note = self.source_note
            self.exit()
            return consumed_source_note

        # If press is on brightness palette -> adjust brightness
        if note in BRIGHTNESS_PALETTE and self.target_entity:
            level = BRIGHTNESS_PALETTE[note]
            logger.info("Picked brightness %s for %s", level, self.target_entity)
            
            # Send to Home Assistant
            try:
                # 255-based brightness
                self.ha_client.call_service(
                    "light", "turn_on", self.target_entity, brightness=int(level * 255)
                )
            except Exception:
                pass
            
            consumed_source_note = self.source_note
            self.exit()
            return consumed_source_note

        # Ignore other buttons while in this mode (return something that signals handled)
        return -1 # Magic value for "handled but ignore"
