# The vinyl chain, and why pads 45/46 go grey

## The chain

```
Sony PS-313 FA  →  amplifier  →  PCM2902 USB ADC  →  Raspberry Pi 3 B (192.168.0.101)
                                                     darkice 1.3 → MP3 320k CBR
                                                     Icecast 2.4.4 :8000/stream
                                                          ↓
                                            Music Assistant (ffmpeg, re-encodes)
                                                          ↓
                                              Sonos SYMFONISK Bookshelf
```

Pad 45 starts it (`script.vinyl_play_on_sonos`), 46 stops it, **74 powers the whole
rig on** (`switch.vinyl`, a Tapo P110).

## The Pi is off most of the time, on purpose

It lives on a switched power strip that gets unplugged when the turntable is not
in use. Forensics in July 2026: **15 listening sessions between 15 April and 28
May, none after**, roughly 8.5 powered days out of 104. Boots lasting 6–7 seconds
appear in the journal — power flicked on and straight off. The Pi has no RTC, so
its logs come back six weeks in the past and none of this is obvious.

That is why pads 45 and 46 are gated on `binary_sensor.vinyl_pi`, a ping sensor
on the Pi (see `PAD_AVAILABILITY` in `config/mapping.py`). The scripts they call
always exist, so without the gate the pads looked live and pressing one could
only fail. The ping integration hardcodes a 30 s poll, so an automation named
*Vinyl Pi - fast presence polling* asks for a refresh on the half-cycle.

Powering the rig from pad 74 takes about **35 seconds** before the stream is
playable: firmware 4 s, userspace to Icecast 21 s, an `ExecStartPre=sleep 5`, and
darkice connecting at ~27 s. The pads going from grey to purple is the signal
that it is ready.

## What used to break it, and what was changed

**A source blip destroyed the mount permanently.** If darkice went quiet,
Icecast dropped the mount and answered `404`. Music Assistant's ffmpeg is started
with `-reconnect_on_network_error 0` and `-reconnect_on_http_error 5xx,429`, so a
404 is precisely the error it will not retry — and MA force-disables flow mode
for radio (`controllers/streams/controller.py`), so it cannot advance the queue
either. Playback ended with no way back.

Fixed with a fallback mount:

```xml
<mount type="normal">
    <mount-name>/stream</mount-name>
    <burst-size>8192</burst-size>
    <fallback-mount>/silence.mp3</fallback-mount>
    <fallback-override>1</fallback-override>
</mount>
```

`/usr/share/icecast2/web/silence.mp3` is 60 s of silence in the same format as
the live mount (44.1 kHz stereo, 320 kbps CBR). **Icecast loops it** — verified
by reading 6 MB across 75 s from a 2.4 MB file — so the mount stays alive
indefinitely and clients are handed back when the source returns.
`<source-timeout>` also went from 10 s to 30 s.

**Stop left a zombie listener.** `script.vinyl_stop` targeted the *native* Sonos
entity while play targeted the *Music Assistant* one, so MA never tore down its
ffmpeg reader and held the Icecast socket open without draining it. Every
session in the archives ended with `Client has fallen too far behind, removing`;
the worst held a socket for 8 hours to transfer 8.8 seconds of audio. Both
scripts now target `media_player.sonos_bookshelf`.

**darkice never got realtime scheduling.** Its config asks for `rtprio 3` but the
unit runs as a normal user, so every start since April logged *"Could not set
POSIX real-time scheduling, this may cause recording skips"*. A drop-in at
`/etc/systemd/system/darkice.service.d/realtime.conf` grants `CAP_SYS_NICE`.

## Latency

**~6 seconds**, down from ~8. The budget:

| Stage | Contribution |
|---|---|
| darkice `bufferSecs` | 1 s (was 5) |
| Icecast `burst-size` 8192 | ~0.2 s (was 65535 ≈ 1.6 s) |
| MA ffmpeg `-readrate_initial_burst 5` | not configurable |
| Sonos radio buffer | not published, not controllable |

The last two are the floor: 6 s is about as good as this architecture gets.
Lowering the bitrate does **not** help — Icecast's burst is measured in bytes, so
fewer kbps means those bytes cover *more* seconds.

Two things that look like levers and are not:

- **FLAC or WAV to the Sonos.** Sonos never sees the Pi's URL; MA re-encodes and
  serves its own, and `providers/sonos/player.py` forces AAC for duration-less
  streams with the comment *"Sonos really does not support FLAC streams without
  duration"*. Optimise the Pi→MA hop, not MA→Sonos.
- **Ethernet instead of WiFi.** On a Pi 3 the NIC hangs off the same USB
  controller as the audio codec. Measured WiFi is −45 dBm with 0% loss, and
  there are no xruns or USB resets in any boot, so there is nothing to fix.

Getting below this means removing hops: a Sonos Era 100 plus the USB-C line-in
adapter (~€234) is 75 ms, but it is a Sonos-only answer — MA cannot redistribute
a Sonos line-in, it is a player-local source rather than an ingestible one.

## Starting by itself when the needle drops

Because the mount now falls back to looping silence, the stream is *always* up
while the Pi has power — which means its audio level alone says whether a record
is playing. Measured on the live stream:

| | mean | peak |
|---|---|---|
| Record playing | −18.4 dB | −3.4 dB |
| Turntable idle | −78.8 dB | −65.2 dB |

Sixty decibels apart, so the threshold is not a delicate choice. In
`configuration.yaml`:

```yaml
binary_sensor:
  - platform: ffmpeg_noise
    name: Vinyl Signal
    input: -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 30 -i http://192.168.0.101:8000/stream
    peak: -40
    duration: 2
    reset: 20
```

The reconnect flags matter: without them ffmpeg exits for good the first time the
power strip is pulled. **Do not set `initial_state: false`** — it does not mean
"assume off", it means *do not start the ffmpeg process at all*, and the entity
then sits `unavailable` forever (`FFmpegBase.available` is `ffmpeg.is_running`).

Two automations drive it, and both guards exist for a reason:

- **Play** fires 5 s after signal appears, but **only if the Sonos is not already
  playing**. Thirty days of history show it busy with AirPlay or Spotify most of
  the time; without that guard, touching the turntable would cut off whatever
  was on.
- **Stop** fires after 5 minutes of silence, but **only while
  `media_player.sonos_bookshelf` still reports `media_content_id:
  library://radio/1`** — the Music Assistant library id for the Vinyl Player
  radio. If playback has moved on to something else, it leaves it alone instead
  of stopping someone's music. Five minutes is long enough to change sides.

A smart plug cannot do this job: a turntable motor draws 1–2 W, below the
P110's reliable resolution, and the plug also feeds the Pi and the amplifier.

## Loose ends

- The Icecast source password is stored in plaintext in `/etc/darkice.cfg`, which
  is world-readable, and repeated in `icecast.xml`.
