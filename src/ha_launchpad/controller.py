"""Launchpad MIDI controller abstraction."""

from typing import Dict, Any, Optional
import time
import threading
import logging
import random

from src.ha_launchpad.utils.rotate_pad import inverse_rotation, rotate_pad
from .config import (
    COLOR_PICK_ENABLED,
    COLOR_PALETTE,
    DISCO_LIGHTS,
    DISCO_SPEED,
    LAUNCHPAD_ALIVE_DELAY,
    LAUNCHPAD_MAX_RETRY_DELAY,
    LAUNCHPAD_RETRY_DELAY,
    LAUNCHPAD_ROTATION,
)
from .backend.mido_backend import MidoBackend


logger = logging.getLogger(__name__)


class LaunchpadController:
    def __init__(
        self, ha_api, button_map: Dict[int, str], backend: Optional[Any] = None
    ):
        if backend is None:
            backend = MidoBackend()

        self.ha_api = ha_api
        self.button_map = button_map
        self.backend = backend
        self.midi_in = None
        self.midi_out = None
        self.running = False
        self.color_pick_mode = False
        self.color_pick_target = None
        self.color_pick_note = None
        self.disco_mode = False
        self.disco_thread = None
        self._press_times: Dict[int, float] = {}
        self._palette_selected_notes = set()
        self._unknown_entities = set()

    def find_launchpad(self):
        """Find and open Launchpad MIDI ports using the provided backend."""
        try:
            found = self.backend.find_and_open()
        except Exception as exc:
            logger.error("MIDI backend error: %s", exc)
            return False

        if found:
            try:
                self.midi_in = self.backend.midi_in
                self.midi_out = self.backend.midi_out
            except Exception:
                self.midi_in = None
                self.midi_out = None

            logger.info("Found Launchpad via backend")
            return True
        return False

    def send_note(self, note: int, color: str, channel: int = 0):
        """Send a MIDI note message to the backend"""
        try:
            physical_note = rotate_pad(note, inverse_rotation(LAUNCHPAD_ROTATION))
            self.backend.send_note(note=physical_note, color=color, channel=channel)
        except Exception:
            logger.warning(
                "Failed to send note via backend: note=%s color=%s", note, color
            )

    def clear_all_leds(self, splash: bool = False):
        """Turn off all LEDs"""
        if self.midi_out:
            if splash:
                for note in range(128):
                    self.send_note(note=note, color="cyan_1")
                time.sleep(0.3)
            for note in range(128):
                self.send_note(note=note, color="")

    def close_backend(self):
        """Close the MIDI backend and reset port references"""
        if hasattr(self.backend, "close"):
            try:
                self.backend.close()
            except Exception:
                pass
        # Reset port references to ensure clean state
        self.midi_in = None
        self.midi_out = None

    def update_led_states(self):
        """Update all mapped LEDs based on HA states"""
        if self.color_pick_mode:
            return

        for note, entity_id in self.button_map.items():
            if self.disco_mode and entity_id in DISCO_LIGHTS:
                continue  # Skip disco lights when disco mode is active

            # Handle special entities
            if entity_id == "disco_toggle":
                if self.disco_mode:
                    disco_button_colors = ["orange_1", "green_1", "cyan_1", "pink_2", "yellow_1"]
                    color = random.choice(disco_button_colors)
                    channel = 2
                else:
                    color = "purple_1"
                    channel = 0
                self.send_note(note, color, channel)
                continue
            elif entity_id.startswith("volume_up.") or entity_id.startswith("volume_down."):
                target_entity = entity_id.split(".", 1)[1]
                # For Google Home devices, only show volume buttons when playing
                if "nestmini" in target_entity or "studio_speaker" in target_entity:
                    target_state = self.ha_api.get_state(target_entity)
                    if target_state and target_state.get("state") == "playing":
                        color = "purple_1"
                    else:
                        color = "off"
                else:
                    color = "purple_1"
                self.send_note(note, color, 0)
                continue

            state_data = self.ha_api.get_state(entity_id)

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
                else:
                    # For Google Home devices and TVs, show LED off when not playing
                    if "nestmini" in entity_id or "studio_speaker" in entity_id or "tv" in entity_id:
                        color = "off"
                    else:
                        color = "amber_1"  # off state for other media players
            else:
                # unknown domain
                self._unknown_entities.add(entity_id)
                color = "red_2"

            self.send_note(note, color, channel)

    def handle_button_press(self, note: int):
        """Handle button press - call HA service"""
        if self.color_pick_mode:
            # If press is on the source pad: exit color-pick. If no palette
            # selection occurred during this pick session, treat it as a
            # short-press toggle for backward compatibility.
            if note == self.color_pick_note:
                if not self._palette_selected_notes and self.color_pick_target:
                    # Short-tap while palette shown -> toggle the entity
                    logger.info(
                        "Source pad released without palette selection -> toggling %s",
                        self.color_pick_target,
                    )
                    try:
                        self.ha_api.toggle_entity(self.color_pick_target)
                        self.send_note(note=note, color="yellow_1", channel=2)
                    except Exception:
                        pass
                self.exit_color_pick_mode()
                return

            # If press is on palette -> pick color
            if note in COLOR_PALETTE and self.color_pick_target:
                r, g, b = COLOR_PALETTE[note]["rgb"]
                logger.info("Picked color %s for %s", (r, g, b), self.color_pick_target)
                # Send to Home Assistant
                try:
                    self.ha_api.call_service(
                        "light", "turn_on", self.color_pick_target, rgb_color=[r, g, b]
                    )
                except Exception:
                    pass
                # Mark that a palette selection happened so release won't toggle
                if self.color_pick_note is not None:
                    self._palette_selected_notes.add(self.color_pick_note)
                # Provide visual feedback on the source pad using palette color name
                try:
                    color = COLOR_PALETTE.get(note, {"color": "white"})["color"]
                    if self.color_pick_note is not None:
                        self.send_note(self.color_pick_note, color, channel=2)
                except Exception:
                    if self.color_pick_note is not None:
                        self.send_note(note=self.color_pick_note, color="green_1")
                self.exit_color_pick_mode()
                return

            # otherwise ignore
            return

        if note not in self.button_map:
            logger.warning("Unmapped button: %s", note)
            return

        entity_id = self.button_map[note]

        # Handle special actions
        if entity_id == "disco_toggle":
            self.toggle_disco_mode()
            return
        elif entity_id.startswith("volume_up."):
            target = entity_id.split(".", 1)[1]
            self.adjust_volume(target, 1)
            return
        elif entity_id.startswith("volume_down."):
            target = entity_id.split(".", 1)[1]
            self.adjust_volume(target, -1)
            return

        # For regular entities, action is toggle
        action = "toggle"
        target_entity = entity_id

        # Skip toggle if entity was not found in Home Assistant
        if target_entity in self._unknown_entities:
            logger.warning(
                "Cannot %s %s - entity not found in Home Assistant",
                action,
                target_entity,
            )
            return

        logger.info("Button %s pressed -> %s %s", note, action, target_entity)

        self.send_note(note=note, color="yellow_1", channel=2)
        success = self.ha_api.toggle_entity(target_entity)
        if success:
            self.send_note(note=note, color="yellow_1", channel=2)

    def enter_color_pick_mode(self, entity_id: str, source_note: int):
        """Enter color pick mode for a target entity and show the palette."""
        self.color_pick_mode = True
        self.color_pick_target = entity_id
        self.color_pick_note = source_note

        # Clear any previous selection markers for a fresh session
        self._palette_selected_notes.discard(source_note)

        # Visual feedback: mark the source pad and draw palette
        try:
            self.send_note(self.color_pick_note, "amber_1", channel=2)
        except Exception:
            pass

        # show palette using single-color notes (no SysEx)
        for note, info in COLOR_PALETTE.items():
            try:
                self.send_note(note, info["color"])
            except Exception:
                pass

    def exit_color_pick_mode(self):
        """Exit color pick mode and restore LED state."""
        self.color_pick_mode = False
        self.color_pick_target = None
        self.color_pick_note = None

        # Clear palette LEDs (best effort) and refresh state
        for note in COLOR_PALETTE.keys():
            try:
                self.send_note(note, "off")
            except Exception:
                pass

    def toggle_disco_mode(self):
        """Toggle disco mode on/off"""
        if self.disco_mode:
            self.disco_mode = False
            if self.disco_thread and self.disco_thread.is_alive():
                self.disco_thread.join()
            self.disco_thread = None
            logger.info("Disco mode disabled")
            # Refresh LED states
            self.update_led_states()
        else:
            self.disco_mode = True
            self.disco_thread = threading.Thread(target=self.disco_thread_func, daemon=True)
            self.disco_thread.start()
            logger.info("Disco mode enabled")

    def disco_thread_func(self):
        """Disco effect thread"""
        disco_colors = [
            (255, 0, 0),    # red
            (0, 255, 0),    # green
            (0, 0, 255),    # blue
            (255, 255, 0),  # yellow
            (255, 0, 255),  # magenta
            (0, 255, 255),  # cyan
            (255, 255, 255),# white
            (255, 128, 0),  # orange
            (128, 0, 255),  # purple
        ]
        while self.disco_mode and self.running:
            for light in DISCO_LIGHTS:
                # Pick a random color for each light
                color = random.choice(disco_colors)
                # Decide to turn on or off randomly
                if random.random() < 0.8:  # 80% chance to turn on
                    self.ha_api.call_service("light", "turn_on", light, rgb_color=color, brightness=255)
                else:
                    self.ha_api.call_service("light", "turn_off", light)
            time.sleep(DISCO_SPEED)

    def adjust_volume(self, target: str, direction: int):
        """Adjust volume up/down"""
        if direction > 0:
            self.ha_api.volume_up(target)
        else:
            self.ha_api.volume_down(target)

    def state_polling_thread(self):
        """Background thread to poll HA states and update LEDs"""
        from .config import POLL_INTERVAL

        logger.info("Starting state polling (interval: %ss)", POLL_INTERVAL)

        while self.running:
            self.update_led_states()
            time.sleep(POLL_INTERVAL)

    def handle_midi_message(self, msg):
        """Process a single MIDI message from the input stream."""
        if msg is None:
            return

        mtype = getattr(msg, "type", None)
        velocity = getattr(msg, "velocity", 0)
        raw_note = getattr(msg, "note", None)
        if raw_note is None:
            return
        note = rotate_pad(raw_note, LAUNCHPAD_ROTATION)

        if note is None:
            return

        # Note-on (press)
        if mtype == "note_on" and velocity > 0:
            self._handle_note_on(note)
            return

        # Note-off (release) or note_on with velocity 0
        if mtype == "note_off" or (mtype == "note_on" and velocity == 0):
            self._handle_note_off(note)

    def _handle_note_on(self, note: int):
        """Handle MIDI note-on (button press)."""
        # If in color-pick mode, process immediately (palette selection)
        if self.color_pick_mode:
            try:
                self.handle_button_press(note)
            except Exception:
                logger.debug("handle_button_press raised", exc_info=True)
            return

        # record press time
        self._press_times[note] = time.time()

        # If this pad supports color-picking, show the palette
        # immediately. A quick release without choosing a palette
        # color will toggle the entity.
        if note in COLOR_PICK_ENABLED and note in self.button_map:
            try:
                entity_id = self.button_map.get(note)
                if entity_id:
                    self.enter_color_pick_mode(entity_id, note)
            except Exception:
                logger.debug("enter_color_pick_mode failed", exc_info=True)

    def _handle_note_off(self, note: int):
        """Handle MIDI note-off (button release)."""
        start = self._press_times.pop(note, None)
        if start is not None:
            duration = time.time() - start
            logger.debug(f"Button {note} was pressed for {duration:.2f} seconds")

        # If a palette selection happened for this source pad,
        # suppress the release-triggered toggle.
        if note in self._palette_selected_notes:
            self._palette_selected_notes.discard(note)
        else:
            try:
                self.handle_button_press(note)
            except Exception:
                logger.debug("handle_button_press failed", exc_info=True)

    def usb_monitor_thread(self):
        """Background thread that continuously monitors Launchpad USB connection."""
        logger.info(
            "Starting USB monitor daemon (check interval: %ss)",
            LAUNCHPAD_ALIVE_DELAY,
        )

        while self.running:
            time.sleep(LAUNCHPAD_ALIVE_DELAY)
            logger.info("USB monitor check")

            connected = self.backend.is_connected()
            if not connected:
                logger.error("Launchpad USB device disconnected")
                logger.info("Signaling shutdown...")
                self.running = False

    def run(self):
        """Main run loop"""

        attempt = 0
        max_attempts = 30  # Retry for ~5 minutes with exponential backoff
        device_found = False

        while attempt < max_attempts:
            attempt += 1
            if self.find_launchpad():
                logger.info("✓ Launchpad HA Controller started!")
                device_found = True
                break

            # exponential backoff delay
            delay = min(
                LAUNCHPAD_RETRY_DELAY * (2 ** (attempt - 1)), LAUNCHPAD_MAX_RETRY_DELAY
            )
            logger.warning(
                "Failed to connect to Launchpad (attempt %d/%d). Retrying in %.1fs...",
                attempt,
                max_attempts,
                delay,
            )
            time.sleep(delay)

        # If Launchpad not found after max attempts, fallback to mock backend
        # if not device_found:
        #     logger.warning(
        #         "⚠️  Launchpad device not found after %d attempts. "
        #         "Switching to mock backend for Home Assistant monitoring only.",
        #         max_attempts,
        #     )
        #     self.backend = MockBackend()
        #     self.find_launchpad()  # Initialize mock backend
        #     logger.info("✓ Mock backend activated - service running in HA-only mode")

        logger.info("Press Ctrl+C to exit")

        self.clear_all_leds(splash=True)
        self.update_led_states()

        self.running = True

        try:
            poll_thread = threading.Thread(
                target=self.state_polling_thread, daemon=True
            )
            poll_thread.start()

            monitor_thread = threading.Thread(
                target=self.usb_monitor_thread, daemon=True
            )
            monitor_thread.start()

            logger.info("Listening for button presses...")

            if self.midi_in is None:
                logger.warning("MIDI input not available - buttons will not work")
                # Still run the polling thread for HA state updates
                while self.running:
                    time.sleep(1)
            else:
                # Use iter_pending() for non-blocking message processing
                while self.running:
                    try:
                        for msg in self.midi_in.iter_pending():
                            self.handle_midi_message(msg)
                        time.sleep(0.1)  # Small delay to prevent CPU spinning
                    except (OSError, ValueError):
                        # Port closed - expected when USB disconnects
                        break
                    except Exception as exc:
                        if self.running:
                            logger.warning("MIDI error: %s", exc)
                        break

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.running = False
            self.clear_all_leds()
            self.close_backend()
            logger.info("Cleanup complete. Goodbye!")
