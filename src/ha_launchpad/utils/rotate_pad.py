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
