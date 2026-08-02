# Apple Home (HomeKit Bridge)

Home Assistant's **HomeKit Bridge** publishes HA entities to Apple Home, so the
same house is reachable from the iPhone Control Centre as well as from the
Launchpad. This is about what that bridge can and cannot be made to do, and what
of this project is reusable there.

## What this project buys you, and what it does not

Nothing in `src/` changes what Apple Home sees. The Launchpad and the bridge are
two independent clients of the same Home Assistant: the controller talks to
`/api/states` and `/api/services`, the bridge is an integration inside HA that
advertises accessories over mDNS. A change to `led_manager` or the standby logic
is invisible to the iPhone, and always will be.

What *is* reusable is [`mapping.py`](../src/ha_launchpad/config/mapping.py). Its
28 entities are the only curated statement anywhere of which entities in this
house are worth a physical control, already grouped by room and already stripped
of the 300 entities that are not. That list is exactly the input the bridge's
`filter` wants, and it has been kept current for a year. Apple Home, by
contrast, was populated once by accepting whatever HA offered.

The gap as of 2026-08-02:

| In `BUTTON_MAP` | In Apple Home |
| --- | --- |
| `light.living_room_spotlights` | yes, "Spotlights" |
| `light.living_room_lamp` | yes, "Lamp" |
| `switch.living_room_bulbs_string` | yes, "Bulbs String" |
| `switch.living_room_neon` | yes, "Neon" |
| `light.bulb_bedroom` | yes, "Lamp" — *No Response* |
| `light.bedroom_lamp` | yes, "Floor Lamp" — *No Response* |
| the 7 scenes | yes, as switches |
| `light.bulb_1`, `light.bulb_2`, `light.bulb_3` | **missing** |
| `switch.vinyl` | **missing** |
| `script.tv_off` | **missing** |
| `media_player.living_room_sonos` | **missing** |
| `media_player.bathroom_speaker` | **missing** |
| `plant.monstera`, `plant.pothos` | not bridgeable, see below |

So the board can do eleven things the phone cannot, and the difference is
entirely configuration.

## Why the scenes are switches and not buttons

This is the thing that looks like a mistake and is not one.

`scene`, `script`, `button` and `input_button` are all in HomeKit's
`ACTIVATE_ONLY_SWITCH_DOMAINS`. HA publishes them as **Switch** accessories that
ignore every turn-off command and reset themselves to off `ACTIVATE_ONLY_RESET_SECONDS`
— **10 seconds** — after being switched on. See
[`type_switches.py`](https://github.com/home-assistant/core/blob/dev/homeassistant/components/homekit/type_switches.py).

They already behave as momentary buttons. What they cannot do is *look* like
one, because the HomeKit accessory protocol has no pressable button:

- **Scenes are not an accessory type.** The scene database belongs to HomeKit
  itself, stored in the home, not to any bridge. A bridge has no way to publish
  one. This is a protocol limit, not an HA omission.
- **Stateless Programmable Switch** — the one service whose name sounds right —
  is *input only*. It reports that a physical button was pressed; the Home app
  cannot press it. Wrong direction.

Hence a toggle showing "Off", which is also why the tile reads `Off` under a
scene name that has no meaningful off state.

### The fix: wrap each one in a native Home scene

A scene created **in the Apple Home app** renders as a square one-tap tile and
fires once. Two already exist here and are the two square tiles in the
screenshot: *Bedroom · Bedtime* and *Bedroom · Sleep Timer*. Everything else is
still the raw pill.

For each of the remaining scene switches:

1. Home app → **+** → **Add Scene** → name it (*I'm Home*, *Bright*, *Sunset*…).
2. **Add Accessories** → pick the HA switch of the same name → set it to **On**.
3. Save, and mark the scene as a favourite.
4. Then find the raw switch accessory, and **turn its favourite off** so the
   duplicate pill disappears from Control Centre. Do not remove the accessory —
   the scene needs it.

The result is a square tile with no state text, identical in behaviour to the
Launchpad pad.

**One honest caveat.** HomeKit activates a scene by writing the target value; if
the switch is already `on`, the write can be a no-op. Since HA drops it back to
off within 10 seconds this only bites when the same scene is tapped twice in
quick succession — the second tap may do nothing. The board has no equivalent
problem because it calls the service directly.

## Naming: the room prefix is HomeKit's, not ours

"Living Room · I'm Home" is the Home app composing *room name* + *accessory
name*. The room comes from the room the accessory was assigned to at pairing
time and is editable only in the Home app. So an accessory should be named for
what it is, not where it is: `Spotlights`, not `Living Room Spotlights`.

`entity_config: <entity>: name:` sets the name a **new** accessory is published
with. It does **not** rename an accessory the Home app already knows: HomeKit
keys accessory settings by accessory id and a user-visible name set on that side
wins permanently. Renaming something already paired is a Home app job — long
press the tile → settings → rename.

Practical consequence: set `name:` for everything now, so the entities being
added for the first time arrive correct, and fix the existing handful by hand.

## Ordering the tiles

Also entirely on the Apple side; the bridge has no say.

- **Home app → Edit Home View** lets tiles be dragged and resized. That order is
  what Control Centre's home controls follow.
- Control Centre shows **favourites**. The fastest cleanup is not reordering but
  removing: unfavourite the raw scene switches once their native scenes exist,
  and unfavourite anything not actually used from the phone.
- Rooms are the coarse grouping, and the two current ones (Living Room,
  Bedroom) already match the two blocks in `BUTTON_MAP`. Keep them aligned; if
  a pad moves rooms on the board, move the accessory too.

An order that mirrors the board reads well in practice: scenes first, then
lights left to right in pad order, then the switches.

## The two "No Response" tiles

Not a HomeKit fault. HomeKit renders an `unavailable` entity as *No Response*,
which is the same information the board shows as a dim grey pad.

- **Bedroom · Floor Lamp** is `light.bedroom_lamp`. Unavailable since
  2026-07-30; its Yeelight config entry retries forever against `192.168.0.14`.
  Already tracked in [`TODO.md`](../TODO.md) as "pad 62 is dead" — the lamp
  changed IP or died.
- **Bedroom · Lamp** is `light.bulb_bedroom`, in the same state.

Fixing the lamps fixes both surfaces at once. Until then the tiles are honest,
so leave them: hiding them would only hide the fault.

## What to add

### `light.bulb_1`, `light.bulb_2`, `light.bulb_3`

Pads 82–84. Individually addressable and colour-capable, and absent from the
phone entirely. The clear win of the whole exercise.

### `script.tv_off`

Pad 58. Becomes an activate-only switch, so wrap it in a native Home scene the
same way. Worth knowing: this script is fire-and-forget through
`google_assistant_sdk` and its failure is silent, so the tile will always look
successful — see [`tv-power-off.md`](tv-power-off.md).

### `media_player.living_room_sonos` and `media_player.bathroom_speaker`

Pads 65–67 and 55–57 spend six pads on volume because the board only has
buttons. Apple Home does this better than the Launchpad can: a media player is
published as a set of switches from `feature_list` (`on_off`, `play_pause`,
`play_stop`, `toggle_mute`), and volume is native. Leaving them off the bridge
is the least defensible omission in the current setup.

### `switch.vinyl`

Pad 74. Exposable, and `type: outlet` is the honest category for a Tapo P110 —
but this plug feeds the Raspberry Pi that runs the vinyl stream, and cutting it
is an unclean shutdown. Publish it if you want the state visible, do **not**
favourite it, and do not put it in any scene where Siri could reach it by
accident.

### The plants

Not bridgeable. There is no `plant` accessory type, and HomeKit has no soil
moisture characteristic. The usual workaround is a template `sensor` with
`device_class: humidity` per plant, which then appears as a humidity sensor —
mislabelled but readable. Worth doing only once the probe work in
[`NEXT.md`](../NEXT.md) has settled; exposing a number that is still being
recalibrated puts a wrong figure on the Home app's summary line.

## The configuration

Goes in HA's `configuration.yaml`. `include_entities` rather than
`include_domains` on purpose — the same reason `BUTTON_MAP` is a list of
entities and not a rule.

```yaml
homekit:
  - name: Home Assistant Bridge
    filter:
      include_entities:
        # living room
        - light.living_room_spotlights
        - light.bulb_1
        - light.bulb_2
        - light.bulb_3
        - light.living_room_lamp
        - switch.living_room_bulbs_string
        - switch.living_room_neon
        - switch.vinyl
        # bedroom
        - light.bulb_bedroom
        - light.bedroom_lamp
        # scenes
        - scene.i_m_home
        - scene.i_m_leaving
        - scene.bedtime
        - scene.goodnight
        - scene.living_room_bright
        - scene.living_room_red
        - scene.living_room_1
        # scripts
        - script.tv_off
        # media
        - media_player.living_room_sonos
        - media_player.bathroom_speaker

    entity_config:
      # Named for what they are; the Home app prepends the room itself.
      light.living_room_spotlights: {name: Spotlights}
      light.bulb_1: {name: Bulb 1}
      light.bulb_2: {name: Bulb 2}
      light.bulb_3: {name: Bulb 3}
      light.living_room_lamp: {name: Lamp}
      switch.living_room_bulbs_string: {name: Bulbs String}
      switch.living_room_neon: {name: Neon}
      # A Tapo P110 really is an outlet, and HomeKit has the category.
      switch.vinyl: {name: Vinyl, type: outlet}

      light.bulb_bedroom: {name: Lamp}
      light.bedroom_lamp: {name: Floor Lamp}

      scene.i_m_home: {name: I'm Home}
      scene.i_m_leaving: {name: I'm Leaving}
      scene.bedtime: {name: Bedtime}
      scene.goodnight: {name: Goodnight}
      scene.living_room_bright: {name: Bright}
      scene.living_room_red: {name: Red}
      # scene.living_room_1 is the entity id; "Sunset" is what it does.
      scene.living_room_1: {name: Sunset}

      script.tv_off: {name: TV Off}

      media_player.living_room_sonos:
        name: Sonos
        feature_list: [on_off, play_pause, toggle_mute]
      media_player.bathroom_speaker:
        name: Bathroom Speaker
        feature_list: [play_pause, toggle_mute]
```

`feature_list` is validated against what the entity actually advertises and the
whole accessory is dropped with an error in the log if it asks for something
unsupported, so start narrow and widen. `on_off` is omitted for the bathroom
Nest Mini deliberately: it reports `idle` rather than `off`, which is the same
quirk noted against pads 55–57 in `mapping.py`.

Note that `type:` is only accepted for the `switch` domain. Scenes and scripts
take `name:` and nothing else — there is no way to make them present as
anything other than a switch, which is what the native-scene wrapper is for.

## Order of work

1. Add the config block above and restart HA. Existing accessories keep their
   ids and their Home app settings; only the new ones appear.
2. Assign the new accessories to Living Room and Bedroom as the Home app asks.
3. Rename the handful of already-paired accessories by hand.
4. Create native Home scenes for the seven scene switches and `TV Off`, then
   unfavourite the raw switches.
5. Reorder in Edit Home View.
6. Fix the two bedroom lamps, which is a Yeelight problem, not this one.

Steps 1 and 2 are the only ones that touch Home Assistant. Everything after is
in the Home app, on the phone, and cannot be scripted from here.
