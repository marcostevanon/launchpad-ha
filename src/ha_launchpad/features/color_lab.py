"""Show the device's whole colour palette on the board, and log what is picked.

Choosing pad colours from a screen does not work. A hex value in a table says
nothing about how bright the LED behind a rubber pad looks in a living room at
night, and the colours this project uses were picked that way. The lab puts all
128 of the Launchpad's colours on the hardware instead: press one, and its
velocity goes to the log, ready to be pasted into `COLORS`.

The grid holds 64 swatches, and the device knows 128, so there are exactly two
pages. They are laid out in the reading order of the palette table on page 11
of the Programmer's Reference, first swatch top left, so the board and the
manual can be held side by side and compared cell for cell.
"""

import logging

from ha_launchpad.config.mapping import (
    ARROW_DOWN_CC,
    ARROW_UP_CC,
    COLOR_LAB_BUTTON_CC,
    LOGO_CC,
)
from ha_launchpad.config.palette import PALETTE_SIZE, describe
from ha_launchpad.infrastructure.midi.interface import MidiBackend

logger = logging.getLogger(__name__)

PAGE_SIZE = 64  # one full 8x8 grid
PAGE_COUNT = PALETTE_SIZE // PAGE_SIZE

# Velocities used by the lab's own furniture rather than as samples.
OFF = 0
WHITE = 3


def pad_for_index(index: int) -> int:
    """The pad holding the index-th swatch of a page.

    Pads are numbered from the bottom left, and the palette table reads from
    the top left, so the first eight swatches land on row 8.
    """
    row, col = divmod(index, 8)
    return (8 - row) * 10 + (col + 1)


PAGE_PADS: tuple[int, ...] = tuple(pad_for_index(i) for i in range(PAGE_SIZE))
PAD_INDEX: dict[int, int] = {pad: index for index, pad in enumerate(PAGE_PADS)}


class ColorLab:
    def __init__(self, backend: MidiBackend, rotation: int = 0):
        self.backend = backend
        self.active = False
        self.page = 0

        self.toggle_button = COLOR_LAB_BUTTON_CC

        # Follow the arrow the user can see, not the one that was printed: at
        # 180 the button silkscreened with an up arrow is pointing down.
        flipped = rotation == 180
        self._previous_page_button = ARROW_DOWN_CC if flipped else ARROW_UP_CC
        self._next_page_button = ARROW_UP_CC if flipped else ARROW_DOWN_CC

    def enter(self) -> None:
        """Open the lab on page 1 and paint the palette."""
        self.active = True
        self.page = 0
        logger.info(
            "Colour lab open: %d colours across %d pages", PALETTE_SIZE, PAGE_COUNT
        )
        self.backend.send_cc(self.toggle_button, WHITE)
        self._paint()

    def exit(self) -> None:
        """Close the lab and blank the furniture around the grid.

        The grid itself is left as-is: the caller repaints it from Home
        Assistant, which it has to do anyway because the lab lights pads that
        no entity owns.
        """
        if not self.active:
            return

        self.active = False
        logger.info("Colour lab closed")

        for cc in (
            self.toggle_button,
            LOGO_CC,
            self._previous_page_button,
            self._next_page_button,
        ):
            try:
                self.backend.send_cc(cc, OFF)
            except Exception:
                logger.debug("Could not clear cc %s", cc, exc_info=True)

    def show_page(self, page: int) -> None:
        if not 0 <= page < PAGE_COUNT or page == self.page:
            return

        self.page = page
        first = page * PAGE_SIZE
        logger.info(
            "Colour lab page %d/%d: velocities %d-%d",
            page + 1,
            PAGE_COUNT,
            first,
            first + PAGE_SIZE - 1,
        )
        self._paint()

    def handle_note(self, note: int) -> bool:
        """Handle a grid press. Returns True when the press was consumed."""
        if not self.active:
            return False

        index = PAD_INDEX.get(note)
        if index is None:
            # Not a pad on the grid. Swallowed anyway: while the lab is open
            # nothing on the board is allowed to reach Home Assistant.
            return True

        velocity = self.page * PAGE_SIZE + index
        logger.info(
            "COLOR %s  page %d  pad %d", describe(velocity), self.page + 1, note
        )

        # Echo the pick on the logo, which is the one LED not showing a swatch.
        # Two samples of the same colour, one of them away from its neighbours,
        # which is where a colour stops borrowing from what surrounds it.
        try:
            self.backend.send_cc(LOGO_CC, velocity)
        except Exception:
            logger.debug("Could not echo the pick on the logo", exc_info=True)

        return True

    def handle_cc(self, control: int) -> bool:
        """Handle one of the buttons around the grid. True when consumed."""
        if not self.active:
            return False

        if control == self._previous_page_button:
            self.show_page(self.page - 1)
        elif control == self._next_page_button:
            self.show_page(self.page + 1)

        # Everything else around the grid is inert while the lab is open,
        # rather than falling through to whatever it would normally do.
        return True

    def _paint(self) -> None:
        if not self.backend.is_connected():
            return

        first = self.page * PAGE_SIZE
        for index, pad in enumerate(PAGE_PADS):
            # Velocity 0 is "off", so the first pad of page 1 is dark. That is
            # the palette telling the truth about itself, not a missing swatch.
            self.backend.send_velocity(pad, first + index)

        # An arrow lights only when it leads somewhere. On two pages that also
        # says which one is open, without a second row of buttons to say it.
        self.backend.send_cc(
            self._previous_page_button, WHITE if self.page > 0 else OFF
        )
        self.backend.send_cc(
            self._next_page_button, WHITE if self.page < PAGE_COUNT - 1 else OFF
        )
