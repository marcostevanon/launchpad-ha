# Waiting on something

Not a task list. The task lists are `TODO.md` here and `home-ops/TODO.md`, and
anything that fits in one of them belongs there instead. This file is only for
things that cannot be started yet, because a part, an event, or a stretch of
time has not arrived, plus decisions that are open and worth not forgetting.

If an entry stops being blocked, it moves to a TODO or gets done. It does not
stay here.

Updated 2026-07-30.

## A part has not arrived

- **SHT31-D and BH1750**, ordered, expected 2026-07-31. Decide the cabling
  before they arrive, see below.
- **A kitchen scale, 10 to 15 kg.** About 15 euros, and it replaces the load
  cell idea entirely. See "the millilitre question".

## An event has to happen on its own

- **One complete watering with the volume weighed.** Weigh the watering can
  before and after, 1 g is 1 mL. Log it in the table in
  `home-ops/services/home-assistant/plants.md`.
- **A few drying cycles** before the "typical so far" band on the Stress chart
  means anything. It was drawn twice and was wrong within hours both times.

## Next time the board is physically open

- **Reflash esphome-01.** The corrected filter comments are in the YAML but not
  compiled.
- **Seal the tops of both soil probes.** Heat-shrink, hot glue or conformal
  coating on the exposed upper section, connector well above the soil line.
  This is what caused the 2026-07-30 outage.
- **A 2:1 divider on both ADC inputs (GPIO32, GPIO33).** 1M/1M with a 100 nF
  cap. The dry calibration anchor sits at **2.65 V** while Espressif specifies
  the usable range at 12 dB attenuation as **150 to 2450 mV**, so everything
  below about 11 to 13% moisture is measured outside spec, and the anchor
  itself was established there. A divider puts the whole 0.90 to 2.65 V span
  into 0.45 to 1.33 V. It halves the mV per point, which costs nothing: the
  chain is already quantisation-limited at about 1.2 LSB.

## Cabling and structure, decide before tomorrow

The pin budget is not the problem. Only four pins are used on esphome-01:
GPIO21/22 for the I2C bus and GPIO32/33 for the two probes. **The SHT31 and the
BH1750 cost zero new pins**, because I2C is a bus and they join the BMP085 at
different addresses (0x44 and 0x23 against 0x77).

The cabling is the problem, and one decision has to be made first:

- **Run the three I2C sensors on ONE four-core cable**, daisy-chained, sharing
  VCC, GND, SDA, SCL. Decide this before mounting or it becomes three separate
  runs that cannot be merged afterwards.
- **The SHT31 must NOT sit near the ESP32 or the BMP085.** The chip runs at
  64 C. It goes at the far end of the cable, at leaf height. This is both an
  accuracy decision and the decision about where the cable runs.
- One three-core cable per probe instead of three jumper wires each. Two runs
  instead of six loose wires.
- A small ABS box, about 5 euros, holding the ESP32 and a screw terminal block,
  fixed to the wall or under the shelf rather than resting on the floor. Every
  cable enters from one side.
- Spiral wrap on the long runs.

Deferred and noted: the plants get good light on the balcony but are in the way
there. Moving them changes the light, which changes the drying rate, so if they
move, mark the date. A step change in the drying rate with no watering is
otherwise indistinguishable from a fault.

## The millilitre question, resolved differently

The permanent load cell is the wrong answer for this flat. The 10 euros is the
electronics only; a 20 kg bar needs two rigid plates and a 28 to 30 cm platform
for a 25 cm pot, raises it three or four centimetres, adds two more cables, and
ends up as a plant standing on a box. On a balcony where the pots are already
bulky that is a bad trade.

**A kitchen scale used by hand does almost all of the same work:**

- **Weigh the can before and after each pour.** 1 g is 1 mL, measured rather
  than estimated. This is exactly the number the "how much did you pour?"
  notification was going to ask for, so the notification is not needed. Put the
  pot in a saucer and weigh the runoff too and you also get drainage, which is
  the single largest error in the whole conversion and always inflates it.
- **Weigh the pot once a week.** Four or five points per drying cycle give the
  curve that converts probe percentage into grams of water, which is what fixes
  `days_until_watering`: it removes the probe nonlinearity, one of two opposing
  30 to 50% biases whose net sign is currently unknown.

What it does not give is continuous automatic measurement. That does not
matter, because watering detection from the probe alone already works with a
very large margin: measured on the filtered signal, a quiet probe moves 0.005
points per reading and has never risen more than 0.7, while a watering gives a
first step of 4 to 6 points (the EMA at alpha 0.2 returns a fifth of the true
jump immediately). **A threshold of +2 points in one five-minute reading sits
three times above the worst observed noise and two times below the smallest
watering, with zero false positives in the data.**

Do not put a mL/day figure on the dashboard until a weighed watering confirms
it. The current chain gives 68.5 mL per point and 290 mL/day, which is
physically plausible (two independent routes, an energy budget and a leaf
conductance calculation, give 95 to 780 and 310 to 590) but sits 2 to 4 times
above horticultural guidance for a 25 cm pot. Drainage biases it high, so a
proper gravimetric measurement should come back nearer **150 to 250 mL/day**.

## Dashboard, three open decisions

The plants view has no technical defects left after the 2026-07-30 audit. What
remains is three quantities that are misleading rather than broken, and all
three are a matter of taste as much as correctness.

- **The Stress chart is the serious one.** The transpiration index divides by
  VPD, which assumes the leaf is coupled to the room air. For a large leaf in
  still indoor air the Jarvis-McNaughton decoupling coefficient is 0.5 to 0.8,
  so the plant is radiation-controlled, not VPD-controlled, and dividing
  over-corrects by roughly a factor of three. On a sunny afternoon VPD rises
  and transpiration rises, both driven by the same sunbeam, the index falls,
  and the note under the chart says "it is closing its stomata". **The
  interpretation is inverted on exactly the days it will be read.** Either take
  it off until the BH1750 arrives, or relabel it as plain drying rate with no
  normalisation. Light is the correct denominator.
- **The VPD bands are greenhouse numbers.** They come from tomato and cannabis
  guidance at 300 to 1000 µmol of light; these plants sit at 10 to 80. A normal
  European home in winter is 1.74 kPa and pothos live in it indefinitely.
  Either widen them (below 0.5 stagnant, 0.5 to 1.8 normal, 1.8 to 2.5 dry,
  above 2.5 genuinely dry) or delete them, as was already done on the Stress
  chart for the same reason.
- **`days_until_watering` is shown to one decimal.** Even with the aliasing
  fixed it carries two opposing 30 to 50% biases. A band, "4 to 7 days", is
  more honest than a point.

Also queued for tomorrow, on the Home view: the **Living room humidity badge**
still reads `sensor.homepod_living_room_humidity`, which arrives 7 times in 12
hours because an iOS Shortcut writes it. Repoint it at the SHT31, then exclude
both HomePod entities from the recorder.

Worth knowing for anything else that touches them: **the two HomePod entities
are not in the entity registry at all.** `POST /api/states` creates a state
without registering an entity, so they cannot be given a display precision, an
area, a device, or any registry setting, and they vanish on every restart. That
is why the Living room temperature badge reads the BMP085 instead: it was the
only way to show a whole number. The BMP085 sits by the window and runs about
1.5 C warmer than mid-room, so the badge and the old tile do not agree, and
that gap closes when the SHT31 replaces both.

## Guards to replace, not loosen

- **The 10% fault floor is fail-dangerous.** It converts "the plant is dying of
  drought" into "no data", its middle premise (dry potting mix reads in the
  teens) is asserted and never measured, and its margin is about one supply sag
  wide: a 100 mV dip during a WiFi burst moves a ratiometric probe 4 to 6
  points. Replace it with a **rate-of-change limit on the post-median signal**:
  the pot moves 0.013 points per five-minute sample, so flag anything above
  0.3, a 20x margin. On the 2026-07-30 log the first step was 5.15 points, so
  this would have fired at 09:28, twenty-five minutes before the floor did, and
  it cannot misfire on a genuinely dry pot.
- **Bound-check the raw voltage before the clamp, not after.** A reading of
  2.9 V is physically impossible for soil and is a perfect fault flag; the
  clamp throws that away and replaces it with a plausible-looking 0%.
- **The -0.8 %/day guard hard-codes health as a precondition for reporting on
  health.** A dying plant does stop drinking, and a healthy pot in winter will
  sit below 0.8 for weeks. Its stated purpose is window warm-up, so gate on
  `buffer_usage_ratio`, which is the quantity actually meant.

## One experiment worth ten minutes

**Put the ESP32 into deep sleep for 30 minutes and watch the BMP085.** The VPD
error budget is dominated by the absolute accuracy of the plant-side
temperature, at 0.184 kPa per degree: the sensor's own spec is ±1 C, which is
±0.18 kPa, against 0.02 to 0.05 kPa for the two-sensor design choice that was
argued about at length. Unquantified self-heating could add another 0 to 2 C on
top. The 04:00 comparison against the bedroom does not settle it, because a
window in July at 04:00 is a strong cold sink and the result is consistent with
both no self-heating and +2 C on a spot that is genuinely colder. Deep sleep
settles it in half an hour.

Related and unquantified: an unshielded sensor in a sunbeam behind glass reads
several degrees high, which is why weather stations use radiation shields. Part
of the measured 3.8 C daily swing is real air and part is radiation error, and
these data cannot separate them.
