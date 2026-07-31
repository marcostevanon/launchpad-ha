# The colour lab

## Why

Every colour on this board was chosen by reading a hex value off a screen. That
does not work. `#8181A1` looks like a slate blue in a browser; behind a rubber
pad, at arm's length, in a living room at night, it is a dim grey smudge — and
it is the colour of every light and every socket that is **switched off**, which
makes it the most-seen colour on the board.

So the picking has to happen on the hardware. The colour lab turns the whole
Launchpad into the palette, and every press writes a line to the log naming the
velocity that was pressed. Press the ones that look right, read them out of the
log, paste them into `COLORS`.

## Opening it

Press **User**. It lights white while the lab is open; press it again to close,
and the board repaints itself from Home Assistant.

Paging is on the **two arrows** at the other end of the same row of round
buttons. At `LAUNCHPAD_ROTATION=180` that row runs along the bottom edge, User
sits at the bottom **left**, and the arrows at the bottom **right**:

```
◆  [User]  ·  ·  ·  ·  ·  [▲]  [▼]
```

> The arrows are followed as the *user* sees them, not as the case printed
> them. Turned 180 degrees the button silkscreened with an up arrow is pointing
> down, so at that rotation ▲ is CC 92 and ▼ is CC 91.
>
> User is picked by name rather than by position for one reason: paging owns
> the arrows, and a button chosen as "the far left of the row" lands *on* an
> arrow at some rotation. The controller tests the lab button first, so that
> collision would silently cost you paging altogether.

## The layout

The device knows **128 colours**, velocity 0 to 127. The grid holds 64. So
there are exactly two pages, and there will never be a third.

| | |
| --- | --- |
| **Grid** | 64 swatches, filled top left first, then along the row |
| **Page 1** | velocities 0–63 |
| **Page 2** | velocities 64–127 |
| **Arrows** | an arrow is lit only when there is a page that way |
| **Logo** | the colour you last pressed |

The lit arrow is also the page indicator. On two pages, "only ▼ is lit" says
you are on the first one as well as a second row of buttons could, and the
side column stays dark rather than carrying eight lights for two states.

The fill order is the reading order of the palette table on page 11 of the
[Programmer's Reference](#where-the-numbers-came-from), so the board and the
manual can be held side by side and compared cell for cell.

The logo is worth its own mention: it is the one LED not surrounded by
sixty-three others, and a colour with nothing next to it is a different colour
from the same one in the middle of a grid. Pressing a swatch echoes it there.

The top-left pad of page 1 stays dark. Velocity 0 is "off", and that is the
palette being honest rather than a swatch failing to light.

## Reading the log

One line per press:

```
2026-07-31 19:04:11,882 INFO … color_lab.py:123: 	COLOR 21 #61FF61 (green_1)  page 1  pad 66
2026-07-31 19:04:14,507 INFO … color_lab.py:123: 	COLOR 87 #61FF61  page 2  pad 68
```

The velocity is the only part that matters — it is what goes into `COLORS` in
[`mapping.py`](../src/ha_launchpad/config/mapping.py). The name in brackets
appears only for the ~40 velocities this project has already named; its absence
means the colour is unclaimed.

The hex is a label, not a promise: it was read off a printed swatch, and a
printed swatch is exactly the thing this whole feature exists to stop trusting.
It is also not unique — the second half of the manual's table repeats several
hues, so velocities 21 and 87 carry the same `#61FF61`. Only the velocity
identifies a colour.

To watch it live from a development machine, with the service running on the
always-on Mac:

```bash
ssh macmini "tail -f ~/Library/Logs/com.launchpad.ha/app.log" | grep --line-buffered COLOR
```

`--line-buffered` is not optional: without it `grep` holds output in a 4 KB
buffer and nothing appears until long after the presses.

## What it deliberately does not do

- **No Home Assistant.** While the lab is open, every press on the board is
  swallowed. Sixty-four pads showing colours are not sixty-four light switches,
  and pressing one to look at a green must not toggle the bedroom. The wake
  button and the restart chord are swatches too while the lab is open; close it
  to get them back.
- **No sleeping.** The idle timer is held off while the lab is open. Falling
  asleep would blank the palette mid-comparison, and the way back in would be a
  button on a board showing nothing.
- **No repainting.** The polling loop leaves the grid alone. It would otherwise
  erase the palette one pad per second as entities changed.

Closing the lab blanks the whole grid before Home Assistant repaints it. The
lab lights all 64 pads including the ones no entity owns, and the LED manager
only knows about the pads in `BUTTON_MAP`, so without the blanking the unmapped
ones would keep their swatches until the next restart.

## Where the numbers came from

The 8x8 grid sends note on/off. Everything around it — the top row, the
right-hand column, the logo — sends **Control Change**, which is why they
appeared dead: the controller read `msg.note` and dropped anything without one.
For lighting, the device accepts either message type on any button.

| | |
| --- | --- |
| Grid | notes 11–88, `row * 10 + column`, row 1 at the bottom |
| Top row | CC 91–98, left to right: up, down, left, right, Session, Drums, Keys, User |
| Right column | CC 89, 79, 69, 59, 49, 39, 29, 19, top to bottom |
| Logo | CC 99 |

All of it is from the *Launchpad Mini [MK3] Programmer's Reference Manual*,
pages 10 and 11.

The 128 hex values in
[`palette.py`](../src/ha_launchpad/config/palette.py) are not in that manual as
text — the colour table is a picture. They were sampled from it, one reading per
swatch. They are there to label a velocity in the log, nothing more.
