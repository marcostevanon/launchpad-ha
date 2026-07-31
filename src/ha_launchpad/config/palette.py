"""The Launchpad Mini MK3's full 128-entry colour palette.

`COLORS` in `mapping.py` names the ~40 velocities this project actually uses.
The device knows 128, numbered 0-127, and the only place they are written down
is the colour table on page 11 of the Launchpad Mini [MK3] Programmer's
Reference Manual, which is a picture rather than a table of numbers. These
hex values were sampled from the swatches in that picture, one per cell.

They exist to *label* a colour in the log, not to reproduce it: an LED behind
a rubber pad never looks like a flat rectangle on a page. Which is the whole
reason the colour lab shows them on the hardware instead.
"""

from ha_launchpad.config.mapping import COLORS

# Indexed by velocity. Row comments match the reading order of the manual's
# table, left to right and top to bottom, so the two can be compared directly.
PALETTE_HEX: tuple[str, ...] = (
    "#616161", "#B3B3B3", "#DDDDDD", "#FFFFFF", "#FFB3B3", "#FF6161", "#DD6161", "#B36161",  # 0-7
    "#FFF3D5", "#FFB361", "#DD8C61", "#B37661", "#FFEEA1", "#FFFF61", "#DDDD61", "#B3B361",  # 8-15
    "#DDFFA1", "#C2FF61", "#A1DD61", "#81B361", "#C2FFB3", "#61FF61", "#61DD61", "#61B361",  # 16-23
    "#C2FFC2", "#61FF8C", "#61DD76", "#61B36B", "#C2FFCC", "#61FFCC", "#61DDA1", "#61B381",  # 24-31
    "#C2FFF3", "#61FFE9", "#61DDC2", "#61B396", "#C2F3FF", "#61EEFF", "#61C7DD", "#61A1B3",  # 32-39
    "#C2DDFF", "#61C7FF", "#61A1DD", "#6181B3", "#A18CFF", "#6161FF", "#6161DD", "#6161B3",  # 40-47
    "#CCB3FF", "#A161FF", "#8161DD", "#7661B3", "#FFB3FF", "#FF61FF", "#DD61DD", "#B361B3",  # 48-55
    "#FFB3D5", "#FF61C2", "#DD61A1", "#B3618C", "#FF7661", "#E9B361", "#DDC261", "#A1A161",  # 56-63
    "#61B361", "#61B38C", "#618CD5", "#6161FF", "#61B3B3", "#8C61F3", "#CCB3C2", "#8C7681",  # 64-71
    "#FF6161", "#F3FFA1", "#EEFC61", "#CCFF61", "#76DD61", "#61FFCC", "#61E9FF", "#61A1FF",  # 72-79
    "#8C61FF", "#CC61FC", "#EE8CDD", "#A17661", "#FFA161", "#DDF961", "#D5FF8C", "#61FF61",  # 80-87
    "#B3FFA1", "#CCFCD5", "#B3FFF6", "#CCE4FF", "#A1C2F6", "#D5C2F9", "#F98CFF", "#FF61CC",  # 88-95
    "#FFC261", "#F3EE61", "#E4FF61", "#DDCC61", "#B3A161", "#61BA76", "#76C28C", "#8181A1",  # 96-103
    "#818CCC", "#CCAA81", "#DD6161", "#F9B3A1", "#F9BA76", "#FFF38C", "#E9F9A1", "#D5EE76",  # 104-111
    "#8181A1", "#F9F9D5", "#DDFCE4", "#E9E9FF", "#E4D5FF", "#B3B3B3", "#D5D5D5", "#F9FFFF",  # 112-119
    "#E96161", "#AA6161", "#81F661", "#61B361", "#F3EE61", "#B3A161", "#EEC261", "#C27661",  # 120-127
)  # fmt: skip

PALETTE_SIZE = len(PALETTE_HEX)

# velocity -> the name this project already gives it, where it has one. Several
# velocities carry the same hex as another (the manual's second block repeats
# hues), so this is keyed on the number, never on the colour.
VELOCITY_NAMES: dict[int, str] = {velocity: name for name, velocity in COLORS.items()}


def describe(velocity: int) -> str:
    """One-line label for a velocity: its hex, plus its name if it has one."""
    if not 0 <= velocity < PALETTE_SIZE:
        return f"{velocity} (out of range)"

    if velocity == 0:
        # The manual draws entry 0 as a grey swatch so it stays visible against
        # the black background of its table. The LED is simply unlit, and
        # printing #616161 for it would be the one dishonest line in the log.
        return "0 unlit (off)"

    name = VELOCITY_NAMES.get(velocity)
    hex_value = PALETTE_HEX[velocity]
    return f"{velocity} {hex_value} ({name})" if name else f"{velocity} {hex_value}"
