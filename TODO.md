# Next up

## Button map
- Confirm which entity actually moves for the bathroom Nest Mini when playback
  starts — Google Assistant voice drives the Cast entity, Music Assistant drives
  `media_player.bathroom_speaker`. Pads 45/46/47 now use the latter.
- Pads 51-54 are held for a `climate.` entity: `midea_ac_lan` is installed but
  currently exposes none.
- See `docs/button-map-proposal.md` for the full analysis.

## Small features worth having
- A `status.<entity>` mapping form: press does nothing, the LED reflects state.
  The plant pads already work this way as a hardcoded special case. Would
  unlock low battery (`sensor.switch_bedroom_battery` is at 10%), humidifier
  overload, pending updates, shopping list.
- `button.press` support, for things like "save the current track".
- `next.` / `prev.` for the Sonos, which supports both.
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

## Button map
- Reclaimed pads 55/56/57 from `media_player.studio_speaker`, unavailable since
  2026-07-22 and without VOLUME_SET, for the living room TV
- Pad 58 controls the Sonos TV autoplay switch
- Pads 45/46/47 moved to `media_player.bathroom_speaker`
- `unavailable` renders as dim grey rather than looking identical to off
- Media players that advertise TURN_ON can be powered on from their pad

## Tech debt
- Separated button configuration, LED rendering and action handling
- Package is installable; imports as `ha_launchpad`
- Dependencies and the interpreter pinned with uv
- Atomic versioned deploys with rollback
