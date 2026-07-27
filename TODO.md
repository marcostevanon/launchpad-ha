# Next up

## Button map
- Repoint pads 55/56/57 — `media_player.studio_speaker` has been unavailable
  since 2026-07-22, and its volume pads could never have worked (the entity has
  no `VOLUME_SET`). The living room TV is unmapped and supports both volume and
  power.
- Repoint pads 45/46/47 to `media_player.bathroom_speaker` rather than the Cast
  entity for the same device, which reports `off` when idle and has no
  next/prev. Verify which entity actually moves when playback starts first.
- See `docs/button-map-proposal.md` for the full analysis and proposed layout.

## Small features worth having
- Render `unavailable` differently from `off`. They are both amber today, so a
  bulb killed at the wall switch looks identical to one that is simply off.
- A `status.<entity>` mapping form: press does nothing, the LED reflects state.
  The plant pads already work this way as a hardcoded special case. Would
  unlock low battery, humidifier overload, pending updates, shopping list.
- `button.press` support, for things like "save the current track".
- `media_player.turn_on` when the player is off and supports it, so a TV pad can
  actually power it on instead of doing nothing.
- Generalise the standby notification indicator beyond plants.

## Error handling
- Show a status pad that lights when a command produced an error
- Send a notification to Telegram when an error is produced

## Bigger ideas
- Hold-for-volume overlay, reusing the brightness picker interaction. Absolute
  instead of relative, one gesture instead of seven presses, and it collapses
  each three-pad media row into one.
- Long-press as a general modifier — `_press_times` already records duration and
  does nothing with it.
- Replace the `volume_up.`/`volume_down.`/`disco_toggle`/`manual_sleep` string
  prefixes with a small dataclass. The prefix grammar is at its limit and is
  what blocks most of the ideas above.
- Colour picker `exit()` should invalidate the LED cache. Until it does, any pad
  in the palette zone (11-14, 21-24, 31-34, 41-44) that also carried a normal
  mapping would be blanked until its entity next changed. Harmless while that
  zone is empty; fixing it makes 16 pads safely usable.

# Completed

## Software restart
- Button chord (15 then 16) restarts the service, now within a 2s window

## Standby / idle
- Sleeps after inactivity, wakes on the dedicated pad
- Slower polling while asleep
- Notification indicator on the wake button
- Changes elsewhere in the house light the affected pads for a couple of
  minutes without waking the board

## Launchpad connection
- Exits non-zero when the Launchpad cannot be found, so the service manager
  restarts it cleanly
- USB monitor exits when the device is unplugged
- Returns the device to Live mode on shutdown

## Rotation
- Board rotation of 0, 90, 180 or 270 degrees

## Extras
- Volume up/down pads
- Disco mode

## Tech debt
- Separated button configuration, LED rendering and action handling
- Package is installable; imports as `ha_launchpad`
- Dependencies and the interpreter pinned with uv
- Atomic versioned deploys with rollback
