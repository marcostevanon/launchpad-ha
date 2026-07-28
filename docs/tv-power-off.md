# Turning the TV off from pad 58

## Why this needs a detour

There is no entity in Home Assistant that can power off the television.

| Thing | What it actually is |
| --- | --- |
| `media_player.living_room_tv` | The **Chromecast** — an "Eureka Dongle" at `192.168.0.9` |
| The television | A **Hisense VIDAA**, present only as ignored `dlna_dmr` entries |

Home Assistant's `cast` integration implements `media_player.turn_off` as
`quit_app()`. It closes whatever is playing and returns the dongle to its
backdrop; it has no way to power down a display. Worse, the cast integration
advertises `TURN_OFF` for *every* device regardless of whether it can do
anything, so Home Assistant shows a power button that lies. This has been
[open since 2016](https://github.com/home-assistant/core/issues/18825).

A local route to the TV was tested and ruled out: with the set switched **on**,
neither the VIDAA MQTT broker (port 36669) nor the DevTools endpoint (port 9223)
answered.

What does work is the voice command. When you say "turn off the TV", Google's
cloud tells the Chromecast to emit an **HDMI-CEC standby** on the wire, and the
TV obeys. That path lives inside the dongle's firmware and is not exposed
locally — but `google_assistant_sdk` can send Google the same sentence. "Turn
off kitchen TV" is one of the examples in the integration's own documentation,
so this is the intended use, not a workaround.

**Prerequisite:** HDMI-CEC must be enabled on the Hisense (Settings → System →
CEC Control). Without it nothing below has any effect.

## Setting up the integration

1. Enable the **Google Assistant API** for a Google Cloud project at
   `console.developers.google.com/apis/api/embeddedassistant.googleapis.com/overview`.
2. **APIs & Services → OAuth consent screen** (now presented as *Google Auth
   Platform*): app name, support email, audience **External**, contact info.
3. **Publishing status → Publish app.** Not optional: credentials for an app
   left in *Testing* expire every 7 days. This is the most common way the setup
   fails a week later.
4. **Clients → Create client**, type **Web application**, authorised redirect
   URI `https://my.home-assistant.io/redirect/oauth`. Copy the client ID and
   secret immediately — the secret cannot be retrieved after the dialog closes.
5. Home Assistant → **Settings → Devices & services → Add Integration → Google
   Assistant SDK**, paste both, authorise.

No billing account and no Workspace account are required.

### If authorisation is refused

> Access blocked: … has not completed the Google verification process.
> The app is currently being tested and can only be accessed by
> developer-approved testers. Error 403: access_denied

That is step 3 not done: the app is still in *Testing*, and this account is not
on its tester list. Publish it rather than adding yourself as a tester —
otherwise the refresh tokens expire weekly.

After publishing, the consent screen warns that Google has not verified the app.
Take *Advanced → Go to … (unsafe)*. The Assistant SDK scope counts as sensitive,
and formal verification only matters for distributing an app to other people.

Do not name the Google Cloud app after a domain you do not own, or publishing
can be refused.

### If the script fails instantly with "Failed to communicate with Google Assistant"

A sub-second failure is a refusal, not a timeout. Home Assistant collapses every
gRPC failure into that one sentence; the real status is only in the log, where
step 1 not being done looks like this:

```
StatusCode.PERMISSION_DENIED
"Google Assistant API has not been used in project <n> before or it is disabled."
```

The Assistant API is per-project and is not enabled by creating credentials.
Enable it, then wait a couple of minutes for it to propagate.

Home Assistant's REST log endpoint was removed, so this traceback is only
reachable over the websocket API (`system_log/list`) or in the UI under
Settings → System → Logs. It is also lost on restart.

## The script

The entity ID must be exactly `script.tv_off`, which is what
[`mapping.py`](../src/ha_launchpad/config/mapping.py) expects.

```yaml
tv_off:
  alias: TV - Turn off (Google Assistant)
  mode: single
  sequence:
    - action: google_assistant_sdk.send_text_command
      data:
        command: "turn off Living Room TV"
```

Two reasons the command is in **English** even though it is spoken in Italian
day to day:

- The device name has to match what Google Home knows, and every Google device
  on this account is named in English ("Living Room TV", "Bathroom speaker").
- Non-English commands take 12–15 seconds end to end against 4–5 for English.

This installation reports `language: en`, `country: DE` — the integration
derives its language from that unless overridden on its Configure page.

To hear the spoken reply, add `media_player: media_player.bathroom_speaker`
under `data:`. That field is only where the *response audio* plays; it does not
target the command.

## How the pad behaves

`script.` was already a supported domain, so no application code was needed.

- The controller calls `script.turn_on`, which returns as soon as the script
  starts rather than waiting for it to finish. The Assistant's several seconds
  of latency therefore never block the polling loop.
- The pad flashes yellow for 0.2 s on press. That confirms the call left, not
  that the TV went off — see below.
- Until the script exists in Home Assistant the pad renders grey and is inert,
  the same as any unreachable device.

## What this cannot tell you

**Failure is silent.** Google stopped returning the text of the Assistant's
reply in March 2026, so the response variable is always empty. If Google accepts
the request but does not act on it, the service still reports success and the
script still reports OK. There is no way to confirm from the call that the TV
actually went off.

When a press appears to do nothing, check
[myactivity.google.com](https://myactivity.google.com/myactivity). If the
command is listed there, Home Assistant and the credentials are fine and the
failure is entirely Google-side.

## Longevity

The integration itself is healthy: promoted to the Gold quality tier in Home
Assistant 2025.12 — two months *after* Gemini for Home began replacing Assistant
on Google devices — with commits through June 2026, its underlying library
updated in July 2026, and no open issues.

Google's side is the risk. The Assistant SDK's sample repository has been
archived since 2022 and its documentation frozen since 2019. There is no
announced shutdown, but capabilities have been disappearing one at a time
without warning: text responses went in March 2026, multi-turn context in late
2025. Expect this pad to stop working some day with no notice, and — because
failure is silent — expect to find out by looking at the TV.

Media playback commands are documented as not working, so this route is for the
television only. See `TODO.md` for the music side.
