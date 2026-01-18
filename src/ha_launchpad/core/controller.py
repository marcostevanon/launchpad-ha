"""Launchpad MIDI controller abstraction."""

from typing import Dict, Any, Optional
import time
import threading
import logging
import random

from src.ha_launchpad.config.settings import (
    LAUNCHPAD_ROTATION,
    LAUNCHPAD_ALIVE_DELAY,
    LAUNCHPAD_RETRY_DELAY,
    LAUNCHPAD_MAX_RETRY_DELAY,
    POLL_INTERVAL,
    DISCO_LIGHTS
)
from src.ha_launchpad.config.mapping import COLOR_PICK_ENABLED, BRIGHTNESS_ENABLED
from src.ha_launchpad.infrastructure.midi.interface import MidiBackend
from src.ha_launchpad.infrastructure.midi.mido_backend import MidoBackend
from src.ha_launchpad.infrastructure.midi.rotated_backend import RotatedBackend
from src.ha_launchpad.infrastructure.ha.client import HomeAssistantClient
from src.ha_launchpad.features.disco import DiscoMode
from src.ha_launchpad.features.color_picker import ColorPicker

logger = logging.getLogger(__name__)


class LaunchpadController:
    def __init__(
        self, 
        ha_client: HomeAssistantClient, 
        button_map: Dict[int, str], 
        backend: Optional[MidiBackend] = None
    ):
        if backend is None:
            backend = MidoBackend()

        # Wrap backend with rotation layer
        self.backend = RotatedBackend(backend, LAUNCHPAD_ROTATION)
        
        self.ha_client = ha_client
        self.button_map = button_map
        
        # Features
        self.disco = DiscoMode(ha_client)
        self.color_picker = ColorPicker(ha_client, self.backend)
        
        self.running = False
        self._press_times: Dict[int, float] = {}
        self._unknown_entities = set()
        self._palette_selected_notes = set()

    def find_launchpad(self):
        """Find and open Launchpad MIDI ports using the provided backend."""
        try:
            found = self.backend.find_and_open()
        except Exception as exc:
            logger.error("MIDI backend error: %s", exc)
            return False

        if found:
            logger.info("Found Launchpad via backend")
            return True
        return False

    def send_note(self, note: int, color: str, channel: int = 0):
        """Send a MIDI note message to the backend"""
        try:
            self.backend.send_note(note=note, color=color, channel=channel)
        except Exception:
            logger.warning(
                "Failed to send note via backend: note=%s color=%s", note, color
            )

    def clear_all_leds(self, splash: bool = False):
        """Turn off all LEDs"""
        if self.backend and self.backend.is_connected():
            if splash:
                for note in range(128):
                    self.send_note(note=note, color="cyan_1")
                time.sleep(0.3)
            for note in range(128):
                self.send_note(note=note, color="")

    def close_backend(self):
        """Close the MIDI backend"""
        if self.backend:
            try:
                self.backend.close()
            except Exception:
                pass

    def update_led_states(self):
        """Update all mapped LEDs based on HA states"""
        # If color pick mode is active, don't update LEDs (let the palette show)
        if self.color_picker.active:
            return

        for note, entity_id in self.button_map.items():
            if self.disco.active and entity_id in DISCO_LIGHTS:
                continue  # Skip disco lights when disco mode is active

            # Handle special entities
            if entity_id == "disco_toggle":
                if self.disco.active:
                    disco_button_colors = ["orange_1", "green_1", "cyan_1", "pink_2", "yellow_1"]
                    color = random.choice(disco_button_colors)
                    channel = 2
                else:
                    color = "orange_1"
                    channel = 0
                self.send_note(note, color, channel)
                continue
            
            elif entity_id.startswith("volume_up.") or entity_id.startswith("volume_down."):
                target_entity = entity_id.split(".", 1)[1]
                # For Google Home devices, show volume buttons when playing or paused
                if "nestmini" in target_entity or "studio_speaker" in target_entity:
                    target_state = self.ha_client.get_state(target_entity)
                    if target_state and target_state.get("state") in ["playing", "paused"]:
                        color = "purple_1"
                    else:
                        color = "off"
                else:
                    color = "purple_1"
                self.send_note(note, color, 0)
                continue

            state_data = self.ha_client.get_state(entity_id)

            if not state_data:
                continue

            state = state_data.get("state", "unknown")
            domain = entity_id.split(".")[0]
            channel = 0

            if domain in ["light", "switch"]:
                if state == "on":
                    if domain == "light" and "attributes" in state_data:
                        brightness = state_data["attributes"].get("brightness", 255)
                        if brightness <= 85:
                            color = "green_3"  # on state dimmed
                        elif brightness <= 170:
                            color = "green_2"  # on state dimmed
                        else:
                            color = "green_1"  # on state
                    else:
                        color = "green_1"  # on state
                else:
                    color = "amber_1"  # off state
            elif domain == "scene":
                color = "blue_1"
            elif domain == "media_player":
                if state == "playing":
                    color = "cyan_0"
                    channel = 2
                elif state == "paused":
                    color = "amber_1"  # paused state
                else:
                    # For Google Home devices, show LED off when off/idle
                    if "nestmini" in entity_id or "studio_speaker" in entity_id:
                        color = "off"
                    else:
                        color = "amber_1"  # off state for other media players
            elif domain == "plant":
                problem = state_data.get("attributes", {}).get("problem", "unknown")
                if problem == "none":
                    color = "green_3"
                    channel = 0
                else:
                    color = "red_2"
                    channel = 2
            else:
                # unknown domain
                self._unknown_entities.add(entity_id)
                color = "red_2"

            self.send_note(note, color, channel)

    def handle_button_press(self, note: int):
        """Handle button press - call HA service"""
        
        # 1. Delegate to Color Picker if active
        if self.color_picker.active:
            res = self.color_picker.handle_input(note)
            if res is not None:
                if isinstance(res, dict):
                    source_note = res.get("source_note")
                    pulse_color = res.get("pulse_color")
                    
                    if source_note:
                        self._palette_selected_notes.add(source_note)
                    
                    if not self.color_picker.active:
                        # Visual feedback: Flash/Pulse
                        if source_note and pulse_color:
                             # Pulse the SOURCE note as requested by user
                             self.send_note(source_note, pulse_color, channel=2)
                             
                             # If we clicked away from source, turn off the palette button
                             if note != source_note:
                                 self.send_note(note, "off")
                                 
                             time.sleep(0.4)
                        
                        # Mode exited, restore LEDs
                        self.update_led_states()
                elif res == -1:
                    pass # Handled but ignore
                
                return True # Input Handled
            return False # Not handled

        if note not in self.button_map:
            logger.warning("Unmapped button: %s", note)
            return

        entity_id = self.button_map[note]

        # 2. Handle special actions
        if entity_id == "disco_toggle":
            self.disco.toggle()
            # Force immediate update of the button state
            self.update_led_states()
            return
            
        elif entity_id.startswith("volume_up."):
            target = entity_id.split(".", 1)[1]
            self.ha_client.volume_up(target)
            return
            
        elif entity_id.startswith("volume_down."):
            target = entity_id.split(".", 1)[1]
            self.ha_client.volume_down(target)
            return

        # 3. Regular entities (toggle)
        if entity_id.startswith("plant."):
            return

        action = "toggle"
        target_entity = entity_id

        if target_entity in self._unknown_entities:
            logger.warning(
                "Cannot %s %s - entity not found in Home Assistant",
                action,
                target_entity,
            )
            return

        logger.info("Button %s pressed -> %s %s", note, action, target_entity)

        # Immediate feedback
        self.send_note(note=note, color="yellow_3", channel=2)
        success = self.ha_client.toggle_entity(target_entity)
        if success:
            # Short delay for the flash to be visible
            time.sleep(0.2)
            self.update_led_states()

    def _handle_note_on(self, note: int):
        """Handle MIDI note-on (button press)."""
        # If in color-pick mode, process immediately
        if self.color_picker.active:
            try:
                self.handle_button_press(note)
            except Exception:
                logger.debug("handle_button_press raised", exc_info=True)
            return

        # record press time
        self._press_times[note] = time.time()

        if note in self.button_map:
            show_colors = note in COLOR_PICK_ENABLED
            show_brightness = note in BRIGHTNESS_ENABLED
            
            if show_colors or show_brightness:
                try:
                    entity_id = self.button_map.get(note)
                    if entity_id:
                        self.color_picker.enter(
                            entity_id, 
                            note, 
                            show_colors=show_colors, 
                            show_brightness=show_brightness
                        )
                except Exception:
                    logger.debug("enter_color_pick_mode failed", exc_info=True)

    def _handle_note_off(self, note: int):
        """Handle MIDI note-off (button release)."""
        start = self._press_times.pop(note, None)
        if start is not None:
            duration = time.time() - start
            logger.debug(f"Button {note} was pressed for {duration:.2f} seconds")

        # CASE 1: Mode is active
        if self.color_picker.active:
            # If the note released IS the source note, handle it
            if note == self.color_picker.source_note:
                 self.color_picker.handle_input(note)
            return

        # CASE 2: Button was just used for a color-pick selection
        if note in self._palette_selected_notes:
            self._palette_selected_notes.discard(note)
            logger.debug("Suppressing toggle handle for %s (already handled by pick)", note)
            return

        # CASE 3: Normal toggle
        try:
            self.handle_button_press(note)
        except Exception:
            logger.debug("handle_button_press failed", exc_info=True)

    def handle_midi_message(self, msg):
        """Process a single MIDI message."""
        if msg is None:
            return

        mtype = getattr(msg, "type", None)
        velocity = getattr(msg, "velocity", 0)
        note = getattr(msg, "note", None)
        
        if note is None:
            return

        # Note-on (press)
        if mtype == "note_on" and velocity > 0:
            self._handle_note_on(note)
            return

        # Note-off (release) or note_on with velocity 0
        if mtype == "note_off" or (mtype == "note_on" and velocity == 0):
            self._handle_note_off(note)

    def state_polling_thread(self):
        """Background thread to poll HA states and update LEDs"""
        logger.info("Starting state polling (interval: %ss)", POLL_INTERVAL)
        while self.running:
            self.update_led_states()
            time.sleep(POLL_INTERVAL)

    def usb_monitor_thread(self):
        """Background thread that continuously monitors Launchpad USB connection."""
        logger.info(
            "Starting USB monitor daemon (check interval: %ss)",
            LAUNCHPAD_ALIVE_DELAY,
        )

        while self.running:
            time.sleep(LAUNCHPAD_ALIVE_DELAY)
            connected = self.backend.is_connected()
            if not connected:
                logger.error("Launchpad USB device disconnected")
                logger.info("Signaling shutdown...")
                self.running = False

    def run(self):
        """Main run loop"""
        attempt = 0
        max_attempts = 30
        
        while attempt < max_attempts:
            attempt += 1
            if self.find_launchpad():
                logger.info("✓ Launchpad HA Controller started!")
                break

            delay = min(
                LAUNCHPAD_RETRY_DELAY * (2 ** (attempt - 1)), LAUNCHPAD_MAX_RETRY_DELAY
            )
            logger.warning(
                "Failed to connect to Launchpad (attempt %d/%d). Retrying in %.1fs...",
                attempt, max_attempts, delay,
            )
            time.sleep(delay)

        logger.info("Press Ctrl+C to exit")
        self.clear_all_leds(splash=True)
        self.update_led_states()

        self.running = True

        try:
            poll_thread = threading.Thread(target=self.state_polling_thread, daemon=True)
            poll_thread.start()

            monitor_thread = threading.Thread(target=self.usb_monitor_thread, daemon=True)
            monitor_thread.start()

            # MIDI Loop
            midi_in = self.backend.iter_incoming()
            if midi_in is None:
                logger.warning("MIDI input not available - buttons will not work")
                while self.running:
                    time.sleep(1)
            else:
                while self.running:
                    try:
                        # Assuming mido port or object that has iter_pending
                        # If backend returns mido port direclty:
                        if hasattr(midi_in, 'iter_pending'):
                             for msg in midi_in.iter_pending():
                                self.handle_midi_message(msg)
                        else:
                            # Fallback if specific backend returns iterator
                            # Note: MidoBackend returns self.midi_in which is a mido Port
                            pass
                            
                        time.sleep(0.1)
                    except (OSError, ValueError):
                        break
                    except Exception as exc:
                        if self.running:
                            logger.warning("MIDI error: %s", exc)
                        break

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.running = False
            self.disco.stop()
            self.clear_all_leds()
            self.close_backend()
            logger.info("Cleanup complete. Goodbye!")
