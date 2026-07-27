# Button map proposal

Reviewed against a live `GET /api/states` (430 entities) and `GET /api/services`
pulled 2026-07-27. Nothing here has been applied — this is for review.

## What is actually controllable

The 430-entity count is misleading: 315 are `sensor.`, and about 160 of those
are Mac mini disk and network telemetry.

| Domain | Count | Notes |
|---|---|---|
| `light` | 7 | 5 RGB-capable, 2 brightness-only |
| `switch` | 12 | 3 real loads, 9 configuration toggles |
| `scene` | 7 | all 7 already mapped |
| `script` | 2 | both already mapped |
| `media_player` | 15 | 6 unavailable AirPlay ghosts, several duplicates |
| `plant` | 2 | both mapped |
| `button` | 12 | none mapped — domain not supported by the app |
| `automation` | 6 | none mapped — domain not supported by the app |
| `climate`, `cover`, `vacuum`, `fan`, `lock`, `alarm`, `timer` | 0 | nothing to bind |

**No entity currently in `BUTTON_MAP` is missing from Home Assistant**, so
nothing is rendering the red "unknown" colour.

`COLOR_PICK_ENABLED` and `BRIGHTNESS_ENABLED` are both already correct against
each light's real `supported_color_modes`. Pads 72 and 61 are brightness-only
lights and are correctly excluded from colour picking. No change needed.

## Dead mappings

### Pads 55 / 56 / 57 — `media_player.studio_speaker`

Dead for three independent reasons:

1. **The device is gone.** `unavailable` since 2026-07-22T15:25:21Z, along with
   every companion entity (`switch.studio_speaker_do_not_disturb`,
   `sensor.studio_speaker_device`, `number.studio_speaker_alarm_volume`, …).
2. **The volume pads could never have worked.** `supported_features: 131968` =
   `TURN_ON | TURN_OFF | PLAY_MEDIA | BROWSE_MEDIA`. No `VOLUME_SET`, so no
   `volume_level` attribute, so `_adjust_volume` logs an error and returns
   `False` on every press — even when the speaker was online.
3. **They are invisible.** `led_manager` special-cases `"studio_speaker"` to
   `("off", 0)` in two places, so all three pads are black on the board today.

### Pads 45 / 46 / 47 — `media_player.nestmini7849`

Not dead, but the wrong entity for the device. Both `nestmini7849` and
`bathroom_speaker` are the same physical Nest Mini
(`sensor.bathroom_speaker_device` = 192.168.0.171). The mapped Cast entity drops
to `off` when idle and lacks `NEXT_TRACK`/`PREVIOUS_TRACK`; the other reports
`idle` and supports the full transport set. The `if "nestmini" in entity_id:
return "off", 0` hack exists precisely to hide the Cast entity's `off` state.

**Verify before switching:** which entity moves depends on how playback starts.
Google Assistant voice drives the Cast entity; Music Assistant drives the other.
Play something and watch both.

### Not dead, despite appearances: pads 61 / 62

Both bedroom lights report `unavailable`, but only recently (today 14:52 and
yesterday 23:25) and both are members of four scenes. They are Wi-Fi bulbs that
drop off when killed at the wall switch. **Keep them.**

This does expose a real gap: `_determine_color` returns amber for any
light/switch that is not `on`, so **`unavailable` looks identical to `off`**.
You cannot currently tell "the bedroom lamp is off" from "the bedroom lamp has
no power".

## Proposed layout

Principles: preserve muscle memory (only pads that are currently black change
meaning), keep the existing column split (1–4 devices by room, 5–8 scenes and
media), keep the palette zone free, and leave deliberate empty space rather than
filling pads for the sake of it.

```
       col 1        col 2        col 3        col 4    │ col 5        col 6        col 7        col 8
row 8  81 SPOTS     82 Spot 1    83 Spot 2    84 Spot3 │ 85 I'm Home  86 Leaving   87 Bedtime   88 Sleep
       (group) ◐☀      ◐☀           ◐☀          ◐☀     │ scene        scene        scene        scene
row 7  71 String    72 LR Lamp ☀ 73 Neon      74  —    │ 75 Bright    76 Red       77 Sunset    78 DISCO
row 6  61 BedBulb ☀ 62 BedLamp◐☀ 63 Humidif.  64  —    │ 65 SONOS ⏯   66 Vol −     67 Vol +     68 SLEEP
row 5  51  —        52  —        53  —        54  —    │ 55 TV ⏯      56 TV Vol−   57 TV Vol+   58 TV→Sonos
       └──── reserved for A/C ────┘                    │ └─────────── CHANGED ───────────┘     └─ NEW ─┘
row 4  41 palette   42 palette   43 palette   44 palet.│ 45 Bath ⏯    46 Vol −     47 Vol +     48  —
row 3  31 palette   32 palette   33 palette   34 palet.│ 35 Vinyl ▶   36 Vinyl ■   37  —        38  —
row 2  21 palette   22 palette   23 palette   24 palet.│ 25  —        26  —        27  —        28  —
row 1  11 palette   12 palette   13 palette   14 palet.│ 15 RESTART①  16 RESTART②  17 Monstera  18 Pothos
       └── transient overlay while a light is held ──┘

  ◐ colour picker   ☀ brightness picker   — intentionally unmapped
```

Rows 8, 7 and 6 are unchanged. The only changes are row 5 and the three
bathroom-speaker pads.

**Row 5, cols 5–8 — the TV row.** Reclaims the three dead pads for the living
room TV in the same play/vol−/vol+ shape as the Sonos row above it, so the
pattern reads as "each media row is one device". Pad 58 gets
`switch.sonos_bookshelf_tv_autoplay`, which decides whether TV audio takes over
the Sonos — semantically the bridge between the two rows.

**Row 5, cols 1–4 — reserved.** `midea_ac_lan` is installed (there is an
`update.midea_ac_lan_update` entity) but exposes no `climate.` entity right now,
so an air conditioner exists on this system and is currently offline. When it
returns, this is where the "left block = physical devices" convention puts it.

### The dict

```python
    # CHANGED: was media_player.studio_speaker (unavailable since 2026-07-22,
    # and it has no VOLUME_SET so 56/57 never worked).
    55: "media_player.living_room_tv",
    56: "volume_down.media_player.living_room_tv",
    57: "volume_up.media_player.living_room_tv",
    58: "switch.sonos_bookshelf_tv_autoplay",   # NEW

    # CHANGED: was media_player.nestmini7849, the Cast entity for the same
    # Nest Mini. Verify which entity moves when playback starts.
    45: "media_player.bathroom_speaker",
    46: "volume_down.media_player.bathroom_speaker",
    47: "volume_up.media_player.bathroom_speaker",
```

Everything else stays as it is.

**Caveat on the TV pad:** `toggle_entity` deliberately does nothing when a media
player is `off` or `unavailable`, so pad 55 cannot turn the TV on as things
stand, and with the TV off there is no `volume_level` either, so 56/57 are inert
too. `media_player.living_room_tv` does support `TURN_ON`. A small change —
call `media_player.turn_on` when the player is off and advertises support — makes
pad 55 a real power plus play/pause control. Worth doing alongside.

## Worth adding, small code changes

| Change | Unlocks |
|---|---|
| Distinct colour for `unavailable` | Tells a bulb with no power apart from one that is off. Your bedroom pads are in that state right now |
| A `status.<entity>` mapping form | Press does nothing, LED reflects state. The plant pads already work this way as a hardcoded special case. Unlocks `sensor.switch_bedroom_battery` (**10% today**), `binary_sensor.humidifier_overloaded`, `update.home_assistant_core_update` (on today), `todo.shopping_list` |
| `button.press` | `button.sonos_bookshelf_favorite_current_song` — "save this track" from the wall. Also the router restart button, which should be behind a chord |
| `next.` / `prev.` | The Sonos supports both; skipping a track needs your phone today |
| `media_player.turn_on` | Makes the TV pad a real power button |

## Rejected for this setup

No `climate.`, `cover.`, `vacuum.`, `fan.`, `lock.`, `alarm.` or `timer.`
entities exist, so blinds, thermostat, vacuum and timer pads have nothing to
bind to. There are no door or window `binary_sensor`s — the five that exist are
phone focus, tablet Bluetooth and humidifier diagnostics. A panic/all-off pad is
already solved by `scene.i_m_leaving` (pad 86), which turns off all eight
lights, the TV and the humidifier. Presence is pointless with a single occupant.

## Structural notes

- **`scene.living_room_1`** has the friendly name "Living Room Sunset". Worth
  renaming the entity in Home Assistant so the mapping comment stops lying.
- **Colour picker cache bug.** `ColorPicker.exit()` writes "off" to all 16
  palette pads directly, bypassing the LED cache, and on the
  release-without-picking path the controller never calls `invalidate_cache()`.
  Any palette pad that also carried a normal mapping would therefore be blanked
  until its entity next changed. Harmless while that zone is empty — but it must
  be fixed before those 16 pads can be used.
- **Entity names hardcoded in LED logic.** `led_manager` contains
  `if "nestmini" in entity_id or "studio_speaker" in entity_id` twice. That is
  configuration living in logic, and both strings refer to entities this
  document recommends dropping.
- **`COLOR_PICK_ENABLED` / `BRIGHTNESS_ENABLED` duplicate knowledge** that is
  already in the states being fetched every second. They could be derived from
  `supported_color_modes` at startup and would then self-correct for new lights.
- **`_unknown_entities`** is collected in `led_manager` and never read.
- **`Unmapped button` logs at WARNING.** With 25+ intentionally free pads —
  including 15 and 16, which you press deliberately every time you arm the
  restart chord — that is warning-level noise during normal use.
