import logging
import random
import threading

from ha_launchpad.config.settings import (
    DISCO_BRIGHTNESS,
    DISCO_LIGHTS,
    DISCO_SPEED,
    DISCO_TRANSITION,
)

logger = logging.getLogger(__name__)

# How far around the hue circle a single step may move. Small enough that the
# bulb's own interpolation sweeps through plausible intermediate hues, large
# enough that each step still reads as a change.
HUE_STEP_MIN = 40.0
HUE_STEP_MAX = 110.0

# Keep colours vivid; washed-out steps look like a fault rather than an effect.
SATURATION_MIN = 85.0
SATURATION_MAX = 100.0


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

        # Set brightness once, up front, and never again while the loop runs.
        #
        # The Trådfri integration carries a single transition_time and hands it
        # to the first attribute command it builds. If brightness is present it
        # takes the transition and the colour change is left with none -- so
        # sending brightness on every step, as this used to, guaranteed the
        # colour would hard-cut no matter what transition was requested.
        for light in DISCO_LIGHTS:
            self.ha_client.call_service(
                "light",
                "turn_on",
                light,
                brightness=DISCO_BRIGHTNESS,
                transition=1,
            )

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(
            "Disco mode enabled (step %.1fs, crossfade %ds)",
            DISCO_SPEED,
            DISCO_TRANSITION,
        )

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
        count = len(DISCO_LIGHTS)
        if not count:
            return

        # Start the bulbs spread around the hue circle so they differ from each
        # other without any of them having to jump a long way.
        hues = [(360.0 / count) * i + random.uniform(0, 30) for i in range(count)]

        # Spread the calls across the interval rather than firing them together:
        # the Trådfri gateway is a CoAP bottleneck and dislikes bursts.
        stagger = DISCO_SPEED / count

        while self.active and not self._stop_event.is_set():
            for i, light in enumerate(DISCO_LIGHTS):
                hues[i] = (hues[i] + random.uniform(HUE_STEP_MIN, HUE_STEP_MAX)) % 360.0
                saturation = random.uniform(SATURATION_MIN, SATURATION_MAX)

                # hs_color, not rgb_color: these bulbs report `hs` as their
                # colour mode, and no brightness here on purpose.
                self.ha_client.call_service(
                    "light",
                    "turn_on",
                    light,
                    hs_color=[round(hues[i], 1), round(saturation, 1)],
                    transition=DISCO_TRANSITION,
                )

                if self._stop_event.wait(stagger):
                    return
