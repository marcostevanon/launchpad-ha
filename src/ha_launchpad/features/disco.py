import threading
import time
import random
import logging
from typing import List

from src.ha_launchpad.config.settings import DISCO_LIGHTS, DISCO_SPEED

logger = logging.getLogger(__name__)

class DiscoMode:
    def __init__(self, ha_client):
        self.ha_client = ha_client
        self.active = False
        self.thread = None
        self._stop_event = threading.Event()

    def start(self):
        if self.active:
            return
        
        self.active = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Disco mode enabled")

    def stop(self):
        if not self.active:
            return

        self.active = False
        self._stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join()
        self.thread = None
        logger.info("Disco mode disabled")

    def toggle(self):
        if self.active:
            self.stop()
        else:
            self.start()

    def _run(self):
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
        
        while self.active and not self._stop_event.is_set():
            for light in DISCO_LIGHTS:
                # Pick a random color for each light
                color = random.choice(disco_colors)
                # Decide to turn on or off randomly
                if random.random() < 0.8:  # 80% chance to turn on
                    self.ha_client.call_service("light", "turn_on", light, rgb_color=color, brightness=255)
                else:
                    self.ha_client.call_service("light", "turn_off", light)
            
            time.sleep(DISCO_SPEED)
