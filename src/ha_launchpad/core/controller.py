"""Launchpad MIDI controller abstraction."""

from typing import Dict, Any, Optional
import time
import threading
import logging

from src.ha_launchpad.config.settings import (
    LAUNCHPAD_ROTATION,
    LAUNCHPAD_ALIVE_DELAY,
    LAUNCHPAD_RETRY_DELAY,
    LAUNCHPAD_MAX_RETRY_DELAY,
    POLL_INTERVAL
)
from src.ha_launchpad.config.mapping import COLOR_PICK_ENABLED, BRIGHTNESS_ENABLED
from src.ha_launchpad.infrastructure.midi.interface import MidiBackend
from src.ha_launchpad.infrastructure.midi.mido_backend import MidoBackend
from src.ha_launchpad.infrastructure.midi.rotated_backend import RotatedBackend
from src.ha_launchpad.infrastructure.ha.client import HomeAssistantClient
from src.ha_launchpad.features.disco import DiscoMode
from src.ha_launchpad.features.color_picker import ColorPicker

# New Logic Components
from src.ha_launchpad.core.logic.led_manager import LEDManager
from src.ha_launchpad.core.logic.input_handler import InputHandler
from src.ha_launchpad.core.logic.feedback_manager import FeedbackManager
from src.ha_launchpad.core.logic.idle_manager import IdleManager

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
        
        # Core Logic Modules
        self.led_manager = LEDManager(ha_client, self.backend, button_map, self.disco)
        self.input_handler = InputHandler(ha_client, button_map, self.color_picker, self.disco)
        self.feedback = FeedbackManager(self.backend)
        self.idle_manager = IdleManager(self.backend)
        
        self.running = False
        self._press_times: Dict[int, float] = {}

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

    def update_led_states(self, force: bool = False):
        """Delegate LED updates to LEDManager"""
        # Checks
        if self.color_picker.active:
            return
            
        is_idle = self.idle_manager.is_idle
        
        # Update logic: If idle, we dry_run to check for changes without lighting up
        # UNLESS force is True (waking up)
        dry_run = is_idle and not force
        
        changed, has_notif = self.led_manager.update_all(dry_run=dry_run)
        
        if is_idle:
            self.idle_manager.set_notification_status(has_notif)
            
            # If HA state changed while idle, we wake up (Remote Wake)
            if changed:
                logger.info("Home Assistant state changed -> Waking up...")
                self.idle_manager.register_activity()
                # Force immediate update to reflect new state
                self.led_manager.update_all(dry_run=False)

    def state_polling_thread(self):
        """Background thread to poll HA states and update LEDs"""
        logger.info("Starting state polling (interval: %ss)", POLL_INTERVAL)
        while self.running:
            self.idle_manager.check_status() # Check for idle timeout
            self.update_led_states()
            
            # Variable polling interval
            if self.idle_manager.is_idle:
                time.sleep(120) # Poll slower when idle
            else:
                time.sleep(POLL_INTERVAL)

    def handle_button_press(self, note: int):
        """Handle button press via InputHandler and execute Feedback"""
        
        # 1. Idle Logic Check
        was_idle = self.idle_manager.is_idle
        
        # Determine if this press should wake up the device
        # For now, we allow ANY button to wake, or stick to WAKE_BUTTON_ID?
        # User said "Show fade button/light to REACTIVATE".
        # Let's say if idle, pressing WAKE_BUTTON_ID wakes up. 
        # Pressing others loops or is ignored?
        # Let's implement: WAKE_BUTTON_ID wakes up. Others ignored (to prevent accidental toggles).
        from src.ha_launchpad.config.mapping import WAKE_BUTTON_ID
        
        if was_idle:
            if note == WAKE_BUTTON_ID:
                self.idle_manager.wake_up()
                # Restore LEDs immediately
                self.update_led_states(force=True)
            else:
                # Glitch Fix: Explicitly turn off stray presses
                self.backend.send_note(note, "off")
            # Ignore other buttons when idle
            return

        # 2. Register Activity (resets timer)
        self.idle_manager.register_activity()

        # 3. Determine actions via Handler
        actions = self.input_handler.handle_press(note)
        
        # 4. Handle Sleep Action
        if actions.get("sleep"):
            self.idle_manager.set_manual_sleep()
            return
        
        # 5. Execute Actions
        if "flash" in actions:
            f = actions["flash"]
            self.feedback.flash(f["note"], f["color"], f["duration"])
            
        if "pulse" in actions:
            p = actions["pulse"]
            self.feedback.pulse(p["note"], p["color"], p["duration"], p.get("clear_note"))
            
        if actions.get("update_leds"):
            self.update_led_states()

    def _handle_note_on(self, note: int):
        """Handle MIDI note-on (button press)."""
        # If in color-pick mode, process immediately via handler
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
                 self.handle_button_press(note)
            return

        # CASE 2: InputHandler tracks selection state
        if self.input_handler.handle_note_off(note):
             return # Suppress default

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
