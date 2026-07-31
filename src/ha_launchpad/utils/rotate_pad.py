def rotate_pad(pad: int, rotation: int) -> int:
    """Rotate an 8x8 Launchpad pad number."""
    row, col = divmod(pad, 10)

    if rotation == 0:
        return pad
    if rotation == 180:
        return (9 - row) * 10 + (9 - col)
    if rotation == 90:
        return col * 10 + (9 - row)
    if rotation == 270:
        return (9 - col) * 10 + row

    return pad


def inverse_rotation(rotation: int) -> int:
    return (360 - rotation) % 360


def reading_order(buttons: tuple[int, ...], rotation: int) -> tuple[int, ...]:
    """Reorder the buttons around the grid to match what the user sees.

    Unlike the pads, these cannot be rotated: they are fixed positions on the
    case, and there is no bottom row or left column for them to land on. Turn
    the board 180 degrees and the top row is along the bottom edge, still the
    same eight buttons, but now running right to left. All that can be fixed is
    the order they are read in, which is what this does.

    At 90 and 270 the row and the column swap edges outright, so "left to
    right" stops meaning anything and the hardware order is returned unchanged.
    """
    return tuple(reversed(buttons)) if rotation == 180 else buttons
