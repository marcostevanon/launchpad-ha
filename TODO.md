# Next up

## Button map
- Confirm which entity actually moves for the bathroom Nest Mini when playback
  starts. Google Assistant voice drives the Cast entity, Music Assistant drives
  `media_player.bathroom_speaker`. Pads 55/56/57 use the latter.
- See `docs/button-map-proposal.md` for the full analysis.

## Move Spotify from the Sonos to the Nest Mini
Pads 47 and 48 are free next to the vinyl pair and are the intended home for
this. Blocked on a decision, not on code.

The Nest Mini is **not a Spotify Connect device**. A scan of the LAN found a
Connect endpoint on the Sonos (`:1400/spotifyzc`) and nothing at all on the Nest,
which only speaks Google Cast. Spotify on a Nest is a *Cast receiver app*, and
the speaker becomes a Connect target only once that app has been launched on it.

Consequences:
- The core `spotify` integration cannot do it. `media_player.select_source` looks
  the device up in `GET /me/player/devices`, where the Nest does not appear until
  it is already playing, and the lookup fails **silently**, so the script would
  report success and do nothing. (The Sonos never appears in that list at all,
  [open since 2017](https://github.com/spotify/web-api/issues/525).)
- `cast` + `media_player.play_media` with a `spotify:` URI does not work either:
  pychromecast's Spotify controller was removed in 9.3.0.
- `google_assistant_sdk` is documented as not supporting media playback.

What works is the Cast `addUser` handshake that launches the Spotify app on the
device first. Two integrations implement it, both HACS custom repositories:
- **`Mincka/spotcast`**, recommended. Successor to `fondberg/spotcast`, which
  its author discontinued on 2026-07-11. Its `transfer_playback` explicitly
  rebuilds `progress_ms`, context, track offset, shuffle and repeat, so the
  handover keeps the exact position.
- **SpotifyPlus**, larger surface and more actively released, but needs a token
  file generated on a desktop and hand-copied into `.storage/`, and its
  maintainer describes position transfer as "erratic".

Costs either way: a Spotify developer app (Premium is required to own one as of
February 2026) and re-authentication roughly every 6 months since refresh tokens
started expiring in July 2026.

Unresolved: whether `GET /me/player` reports track and position for the Sonos
virtual-line-in session at all. If not, only "start Spotify on the Nest" is
possible and "move what is playing" is not. Installing the core `spotify`
integration answers this in two minutes.

## Small features worth having
- A `status.<entity>` mapping form: press does nothing, the LED reflects state.
  The plant pads already work this way as a hardcoded special case. Would
  unlock low battery (`sensor.switch_bedroom_battery` is at 10%), the vinyl
  plug being overloaded, pending updates, shopping list.
- `button.press` support, for things like "save the current track".
- `next.` / `prev.` for the Sonos, which supports both.
- Generalise the standby notification indicator beyond plants.

## Error handling
- Show a status pad that lights when a command produced an error
- Send a notification to Telegram when an error is produced

## Bigger ideas
- **Stop polling. Subscribe.** Every poll is `GET /api/states`, which returns
  **all 329 entities, 159 KB, 44 ms**, to drive 30 pads that reference **28
  entities**. At `POLL_INTERVAL` 1.5s that is 6.4 MB/min awake, and at
  `IDLE_POLL_INTERVAL` 10s another 954 KB/min asleep: roughly **2.7 GB a day**.
  It costs no bandwidth that matters (the mini and the HA VM are both wired, and
  the VM is bridged on the mini itself, so none of it touches WiFi) but it does
  mean Home Assistant serialises 329 entities to JSON forty times a minute on a
  VM already short of CPU.

  The websocket `subscribe_entities` command with an entity filter fixes all of
  it at once: Home Assistant pushes only the mapped entities and only when they
  change. Cuts the traffic by ~99%, removes the up-to-1.5s lag so pads react the
  instant a scene fires, and makes the awake/asleep interval distinction mostly
  moot because there is no polling left to slow down. Touches `client.py` and
  `led_manager.update_all`, and needs a reconnect/backoff path that the current
  stateless polling gets for free. Raising the intervals instead would be the
  wrong fix: still 329 entities fetched to read 28, just less often.
- Hold-for-volume overlay, reusing the brightness picker interaction. Absolute
  instead of relative, one gesture instead of seven presses, and it collapses
  each three-pad media row into one.
- Long-press as a general modifier. `_press_times` already records duration and
  does nothing with it.
- Replace the `volume_up.`/`volume_down.`/`disco_toggle`/`manual_sleep` string
  prefixes with a small dataclass. The prefix grammar is at its limit and is
  what blocks most of the ideas above.
- Colour picker `exit()` should invalidate the LED cache. Until it does, any pad
  in the palette zone (11-14, 21-24, 31-34, 41-44) that also carried a normal
  mapping would be blanked until its entity next changed. Harmless while that
  zone is empty; fixing it makes 16 pads safely usable.

# Completed

## Vinyl
- Pad 74 powers the rig; 45 and 46 stay grey until the Raspberry Pi answers a
  ping, because the Pi lives on a switched strip and is off most of the time
- The Icecast mount now falls back to looping silence, so a source blip no
  longer ends playback permanently
- Latency ~8s to ~6s, which is the floor for this architecture
- Starts itself when the needle drops and stops after the record ends,
  without hijacking the Sonos when it is playing something else
- See `docs/vinyl-streaming.md`

## TV
- Pad 58 powers the television off through `google_assistant_sdk`, which is
  the only route that reaches it: the cast integration's turn_off is just
  quit_app(), and the Hisense answers nothing locally. See
  `docs/tv-power-off.md`.

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
