# The vinyl chain

```
Sony PS-313 FA  →  amplifier  →  PCM2902 USB ADC  →  Raspberry Pi 3 B (192.168.0.101)
                                                     darkice 1.3 → MP3 320k CBR
                                                     Icecast 2.4.4 :8000/stream
                                                          ↓
                                            Music Assistant (ffmpeg, re-encodes)
                                                          ↓
                                              Sonos SYMFONISK Bookshelf
```

The turntable starts and stops the Sonos by itself. Pad **74** (`switch.vinyl`, a
Tapo P110) powers the rig, and it is the only vinyl pad left on the board.

Home Assistant's side of this, the threshold and the measurements behind it, is
in `home-ops/services/home-assistant/vinyl.md`. What follows is the Pi.

## The strip stays on

It used to be switched off between sessions, which killed the stream at the
source and cost about **35 seconds** to come back: firmware 4 s, userspace to
Icecast 21 s, an `ExecStartPre=sleep 5`, darkice connecting at ~27 s. Leaving it
on removes that whole class of failure, and the only things that change now are
the turntable's own switch and the needle.

`binary_sensor.vinyl_pi`, a ping sensor, still reports whether the Pi answers.

## What used to break it, and what was changed

**A source blip destroyed the mount permanently.** If darkice went quiet,
Icecast dropped the mount and answered `404`. Music Assistant's ffmpeg is started
with `-reconnect_on_network_error 0` and `-reconnect_on_http_error 5xx,429`, so a
404 is precisely the error it will not retry, and MA force-disables flow mode
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
the live mount (44.1 kHz stereo, 320 kbps CBR). **Icecast loops it**, verified by
reading 6 MB across 75 s from a 2.4 MB file, so the mount stays alive
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

**~6 seconds** of audio delay, down from ~8. The budget:

| Stage | Contribution |
|---|---|
| darkice `bufferSecs` | 1 s (was 5) |
| Icecast `burst-size` 8192 | ~0.2 s (was 65535 ≈ 1.6 s) |
| MA ffmpeg `-readrate_initial_burst 5` | not configurable |
| Sonos radio buffer | not published, not controllable |

The last two are the floor: 6 s is about as good as this architecture gets.
Lowering the bitrate does **not** help, because Icecast's burst is measured in
bytes, so fewer kbps means those bytes cover *more* seconds.

Two things that look like levers and are not:

- **FLAC or WAV to the Sonos.** Sonos never sees the Pi's URL; MA re-encodes and
  serves its own, and `providers/sonos/player.py` forces AAC for duration-less
  streams with the comment *"Sonos really does not support FLAC streams without
  duration"*. Optimise the Pi→MA hop, not MA→Sonos.
- **Ethernet instead of WiFi.** On a Pi 3 the NIC hangs off the same USB
  controller as the audio codec. Measured WiFi is −45 dBm with 0% loss, and
  there are no xruns or USB resets in any boot, so there is nothing to fix.

Getting below this means removing hops: a Sonos Era 100 plus the USB-C line-in
adapter (~€234) is 75 ms, but it is a Sonos-only answer, because MA cannot
redistribute a Sonos line-in. It is a player-local source rather than an
ingestible one.

## Detection: the meter, not the microphone

Listening to the stream was the original answer and it is gone. An
`ffmpeg_noise` binary sensor pointed at the Icecast mount looked right on paper,
60 dB between a record and an idle turntable, and it failed in both directions
within a single evening on 2026-07-30: it reported records with the platter
stopped, and it went deaf for thirteen minutes while the stream measured
−21.6 dB mean. The underlying bug is open upstream since 2017, ffmpeg's stderr
progress output blocking the same pipe Home Assistant parses for
`silencedetect`, and `extra_arguments: -nostats` did not fix it.

**A smart plug can do this job after all**, which is the opposite of what this
page used to claim. The old note said a turntable motor draws 1-2 W, below the
P110's reliable resolution. Measured properly, the motor is worth **0.27 W**
against 0.10 of noise, and the two populations meet in a single 0.1 W bin. A cut
at 5.25 W never missed a spinning platter across 51 readings. The claim was
never measured, only assumed.

It works because the PS-313 is fully automatic: the arm returns and the platter
stops at the end of a side, so one threshold covers starting and stopping.

## Loose ends

- The Icecast source password is stored in plaintext in `/etc/darkice.cfg`, which
  is world-readable, and repeated in `icecast.xml`.
