# Open items, 2026-07-29

Scratch handover, deliberately not committed. The durable lists live in
`TODO.md` here and in `home-ops/TODO.md`; this file only collects what is
actually next, plus the one item that had fallen out of both.

## Tomorrow, while you are at the plant anyway

- **Water the Monstera, and measure the water in millilitres.** One jug, one
  number, once. It converts the transpiration index from arbitrary units to
  mL/day/kPa, which is comparable with published figures and also answers "how
  much do I pour". There is no way to recover this number later.
- **Read the overnight packet loss** on both ESP32 boards. Tonight is the first
  clean night: today had four reflashes in it.
- **Buy SHT31-D (or SHT4x) and BH1750.** They go on the I2C bus `esphome-01`
  already runs: `bus_a`, SDA GPIO21, SCL GPIO22, BMP085 at 0x77. SHT at 0x44,
  BH1750 at 0x23, no address clash. Do not save three euros on a DHT22: at 26 C
  a 3 point error in relative humidity is 0.10 kPa of VPD, a tenth of the
  distance between "comfortable" and "stressful". Mount it near the plants, not
  by the window, so one device gives both room humidity and the temperature at
  the leaves.

## Sendspin, the piece that had fallen out

This is the one that was missing from every list. Music Assistant **2.8**
introduced **Sendspin Bridges**, which wrap the Sendspin protocol around
existing Chromecast and AirPlay devices so they can sit in one synchronised
group. It is the answer to "one name in the Spotify picker and one in the
AirPlay picker, both playing on the Sonos and the Nest Mini in sync".

State as of today:

```
Music Assistant     2.9.9, up to date      bridges available since 2.8
sendspin players    none                   never configured
Sonos               media_player.living_room_sonos     (AirPlay side)
Nest Mini           media_player.nestmini7849          (Cast side)
```

Sequence: enable the Sendspin provider, create a bridge for each of the two
devices, build a Sync Group containing both, then add the Spotify Connect
provider and the AirPlay Receiver provider **for that group player** (they are
configured per player).

Known risks, from the research done earlier: both plugins are `"stage":
"alpha"`, Sendspin itself is Technical Preview and 16 bit only, transport
commands lag 0.5 to 5 s for Spotify Connect and about 5 s for the AirPlay
receiver, and the Cast half is the fragile half. The docs say AirPlay to
Sendspin bridges should always work, Cast bridging "is not guaranteed to work
due to device firmware limitations".

This is the same project as **"Move Spotify from the Sonos to the Nest Mini"**
in `TODO.md`, which has been sitting at *blocked on a decision, not on code*.
Pads 47 and 48 are free and are the intended home for it.

## Plants and ESPHome

- **Per pot thresholds.** Both plants are configured with `min_moisture: 30`.
  The Monstera cycles 86 to 30 in ten days; the Pothos has never been below
  60.8 in sixty days of history. That threshold describes one of them. Needs
  watering-event detection and a few cycles of data first.
- **When the sensors arrive:** wire them, point `sensor.living_room_vpd` at the
  real hygrometer, then exclude the two HomePod entities from the recorder.
  Those two are written by an iOS Shortcut through `POST /api/states`, cannot be
  range-checked, and vanish from the state machine on every restart, taking the
  whole VPD chain with them.
- **The "typical so far" band** on the transpiration chart, after a few drying
  cycles produce an honest range. It was drawn twice and was wrong within hours
  both times.

## Launchpad

- **Stop polling, subscribe.** Today it is `GET /api/states` every 1.5 s: all
  329 entities, 159 KB, to drive 30 pads referencing 28 entities. Roughly 2.7 GB
  a day and 329 entities serialised forty times a minute on a VM already short
  of CPU. `subscribe_entities` with an entity filter fixes traffic, lag and the
  awake/asleep distinction at once. Touches `client.py` and
  `led_manager.update_all`, needs a reconnect/backoff path.
- **Error handling**: a status pad that lights on a failed command, and a
  Telegram message when one is produced.
- **`status.<entity>` mapping form** (press does nothing, LED reflects state).
  The plant pads already work this way as a hardcoded special case. Unlocks low
  battery, the vinyl plug being overloaded, pending updates, shopping list.
- Confirm which entity actually moves for the bathroom Nest Mini when playback
  starts, see `docs/button-map-proposal.md`.

## Infrastructure, the two serious ones

- **Time Machine silently skips the Home Assistant VM.** Fusion holds the
  `.vmdk` open and never bumps its mtime, so TM hardlinked one **7 July** copy
  into every later snapshot. This is why the outage cost fifteen days.
- **NordVPN owns the mini's default route.** When the app logs itself out, which
  it does unprompted, restic, Home Assistant and the tunnels fail together, and
  macOS has no non-interactive way to log back in. Root cause of the July
  outage.

## Security

- Recovery codes are in Google Drive, which is a circular dependency. Move to
  KeePass plus paper.
- Update VMware Fusion: VMSA-2026-0003 / CVE-2026-41702, privilege escalation,
  upgrading is the only remedy.
- MQTT broker password in plaintext in two places
  (`/usr/local/bin/theengs_gateway.sh`, `~/docker/bluetooth/docker-compose.yml`).

## Documentation

- The Raspberry Pi is not in `home-ops/machines/` at all, and its Theengs entry
  is now wrong since the container was stopped on 2026-07-28.
- Review the Telegram bots and delete the unused ones.

## My own debt

- `recorder/import_statistics` is being called without `unit_class` and
  `mean_type`. Home Assistant warns this stops working in **Core 2026.11**. It
  affects the backfill scripts, not your configuration.

## What changed today, so the state is not a surprise

- Pothos drying window 24h to 72h (Monstera stays at 24h), because a 24 hour
  slope on that pot carries a 25% error and 25% of sixteen days is four days of
  chart jitter. Hourly jitter 0.88 to 0.37 days.
- Days-until-watering history rebuilt and re-imported on the new windows, hours
  whose window straddles a watering dropped rather than smoothed.
- VPD reconstructed for about 22 hours, which is as far back as any instrument
  in the flat measured humidity. Outdoor humidity was tested as a stand-in and
  rejected: r = -0.17.
- Watering and Air charts now carry a live raw tail that owns the header and the
  legend, so every printed number on the page agrees.
- `Plants - moisture low` gained a forecast trigger and a 09:00 trigger, and is
  now silent only between 22:00 and 08:00 instead of always.
- `home-v2` is the default dashboard. `Essential` deleted, copy in
  `essential_view_backup.json` next to this file and in the daily HA backup. `Overview` deliberately left in place.
- The dashboard had been stuck in edit mode across reloads, which is what
  silently overwrote four saves earlier today. Closed.
