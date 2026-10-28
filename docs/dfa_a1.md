# DFA a1 – In-Ride Aerobic Threshold Marker

This document collects everything about the DFA alpha 1 analysis in
intervals-icu-sync in one place: what the metric is, how it is derived from
your head unit's data, which fields it adds to the coach dataset, how the
coach is instructed to read it, and where its limits are.

---

## 1. What DFA a1 is

**DFA** stands for *Detrended Fluctuation Analysis*, **a1** for *alpha 1*,
the short-term scaling exponent of that analysis. Applied to the intervals
between consecutive heartbeats (R-R intervals), it answers one question:

> How strongly do consecutive heartbeat intervals depend on each other?

The result is a dimensionless number, typically between ~0.3 and ~1.5:

| alpha 1 | Character of the series | Physiology |
| ------- | ----------------------- | ---------- |
| ≈ 1.5   | Brownian motion – every beat follows the previous one | strongly correlated, both autonomic branches active |
| ≈ 1.0   | 1/f noise – complex, self-similar | healthy resting state, easy endurance |
| ≈ 0.75  | transition | **aerobic threshold (LT1 / VT1)** – upper end of Zone 2 |
| ≈ 0.5   | white noise – beats independent of each other | parasympathetic withdrawal; discussed as anaerobic threshold (LT2) |
| < 0.5   | anti-correlated – long follows short | very high intensity; value no longer informative |

The key property: **DFA a1 falls continuously as intensity rises.** It is
therefore an intensity-dependent signal *during* the ride, not a daily value.

### DFA a1 is not "HRV"

The project already uses HRV in two places. They must never be confused:

| | Wellness HRV | DFA a1 |
| --- | --- | --- |
| Source | nightly / resting measurement → `/wellness` | R-R intervals of the activity → `/activity/{id}/streams` |
| Metric | RMSSD (ms) – *how large* is the variability | scaling exponent – *how structured* is the variability |
| Question answered | How recovered am I today? | How hard was this ride for my autonomic system, and where is my aerobic threshold today? |
| Location in dataset | `metrics.hrv`, `metrics.wellness_trends.hrv` | `activities[].dfa_a1_summary`, `week_summary.aerobic_threshold_estimate` |

Field names in the new data deliberately never contain a bare `hrv`; they
all start with `dfa_a1_`.

### Where it comes from

- DFA was introduced by Peng et al. (1994/95) in statistical physics,
  originally for DNA sequences and cardiology (heart rhythm complexity).
- That alpha 1 drops systematically under exercise has been known since the
  2000s (Hautala, Tulppo et al.).
- Gronwald, Rogers and Hoos (2020/21) showed that the crossing of 0.75
  agrees well with the first ventilatory/lactate threshold on a group level,
  which triggered its adoption in endurance sport (AlphaHRV data field,
  Fatmaxxer, Kubios, Runalyze, …).

---

## 2. Prerequisites on the athlete side

1. **A chest strap that transmits R-R intervals.** Optical wrist/arm
   sensors do not provide beat-to-beat data of sufficient quality. Garmin
   HRM-Pro/HRM 600/HRM 200 and Polar H9/H10 work; Polar straps are the
   reference in the literature.
2. **HRV logging enabled on the head unit.** Garmin Edge: *System → Data
   Recording → Log HRV*. Without this the FIT file contains only the
   heart rate, not the individual beats.
3. **An activity synced to intervals.icu.** intervals.icu imports the beats
   as an `hrv` stream. It is stored but not displayed as a chart, so you
   will not see it in the web UI – the data is there nonetheless.

No third-party data field (e.g. AlphaHRV) is required: the project computes
alpha 1 itself from the raw `hrv` stream. That also means older activities
recorded with HRV logging can be analyzed retroactively.

---

## 3. How the project computes it

Implementation: [`src/intervals_icu/dfa_a1.py`](../src/intervals_icu/dfa_a1.py)
(pure Python, no additional dependencies).

### Input

The `hrv` stream has one entry per second: `null` when no beat ended in that
second, otherwise a list of R-R intervals in milliseconds, e.g. `[662, 635]`.
It is fetched together with `time`, `watts` and `heartrate` in a single
request filtered with `?types=`.

### Steps

1. **Parse beats** – flatten the stream into `(time_s, rr_ms)` pairs.
2. **Artifact filter** – a beat deviating by more than **20 %** from its
   predecessor is marked invalid (missed/double detections, ectopic beats).
3. **Sliding windows** – **120 s** wide, advanced every **30 s** (75 %
   overlap). A window needs ≥ 60 beats.
4. **Per window** – on the clean beats:
   - subtract the mean and cumulate → profile y(k)
   - cut the profile into boxes of n = 4 … 16 beats
   - fit a straight line in each box and compute the RMS residual F(n)
     ("detrended")
   - the slope of log F(n) vs. log n is **alpha 1**
   - average power and heart rate of the same 120 s are stored alongside
5. **Window quality** – windows in the first **10 minutes** (strap not yet
   settled, window not yet filled) or with > **5 %** artifacts are dropped.
6. **Summary** – from the remaining windows (see fields below).

### Activity quality gate

A ride is `valid: false` (with a `reason`) when

- R-R coverage < **50 %** of ride seconds (connection gaps, strap not worn),
- activity-wide artifact rate > **10 %** (poor electrode contact), or
- fewer than **10** usable windows remain after warm-up.

### Which rides are analyzed

Mirroring the W'bal gate (hard rides only), the DFA gate selects the
*opposite* class of rides in
[`scripts/prepare_activities_for_coach.py`](../scripts/prepare_activities_for_coach.py):

| Condition | Why |
| --- | --- |
| `stream_types` of the activity contains `hrv` | cheapest possible filter – no stream download for rides without beat data |
| moving time ≥ 60 min | shorter rides rarely reach steady state |
| heart-rate data present | |
| Z5+ share < 10 % | alpha 1 saturates near 0.5 at high intensity |
| no `Race` type, no `vo2*` or `event` tag | same reason |
| at most the **3 newest** qualifying rides per run | keeps pipeline latency predictable (each analysis is one extra stream request of ~160 KB and ~0.3 s CPU) |

The stream is downloaded **once** per ride and shared between the W'bal and
DFA a1 analyses.

### Validation

[`tests/test_dfa_a1_analysis.py`](../tests/test_dfa_a1_analysis.py) checks
the mathematical calibration (white noise → alpha ≈ 0.5, random walk →
alpha > 1.2), the quality gates, the activity gate and the weekly aggregate.
A real 2-hour ride recorded with a Garmin HRM 200 on an Edge 1050 yielded
99.7 % coverage and 1.5 % artifacts.

---

## 4. Fields in the coach dataset

### Per ride – `activities[].dfa_a1_summary`

Present **only** for rides that pass the gate; the key is omitted entirely
otherwise (consistent with how `decoupling` is omitted for rides without
power).

```json
"dfa_a1_summary": {
  "valid": true,
  "artifact_pct": 1.5,
  "coverage_pct": 99.7,
  "windows_total": 262,
  "windows_valid": 222,
  "avg": 1.21,
  "time_above_0_75_pct": 92,
  "time_below_0_5_pct": 0,
  "power_at_0_75": 170,
  "hr_at_0_75": 125,
  "threshold_windows": 18
}
```

| Field | Meaning |
| --- | --- |
| `valid` | `false` when the quality gate failed; then only `artifact_pct`, `coverage_pct` and `reason` are present |
| `artifact_pct` | share of beats rejected by the 20 % jump filter – *are the data clean?* |
| `coverage_pct` | share of ride seconds that contain at least one beat – *are the data there?* (connection gaps vs. contact problems are different failure modes) |
| `windows_total` / `windows_valid` | 120 s windows computed, and those kept after warm-up and the 5 % window filter |
| `avg` | mean alpha 1 over valid windows |
| `time_above_0_75_pct` | share of valid windows above the aerobic-threshold marker – *was this really a Zone 2 ride?* |
| `time_below_0_5_pct` | share of valid windows below the 0.5 marker |
| `power_at_0_75` / `hr_at_0_75` | mean power and heart rate of the windows with alpha 1 in **0.65–0.85** – today's LT1 estimate for this ride; `null` when fewer than 3 such windows exist |
| `threshold_windows` | how many windows supported that estimate (confidence indicator) |

Invalid example:

```json
"dfa_a1_summary": {
  "valid": false,
  "artifact_pct": 14.2,
  "coverage_pct": 98.0,
  "reason": "artifact rate 14.2% above 10%"
}
```

### Per week – `week_summary.aerobic_threshold_estimate`

Built by [`scripts/analyze_week.py`](../scripts/analyze_week.py) from the
per-ride summaries of the lookback window. Present only when at least one
ride is `valid`. **No multi-week trend** is computed – the dataset focuses on
the current lookback; longer-term tracking is left to the athlete in
intervals.icu.

```json
"aerobic_threshold_estimate": {
  "rides_with_valid_data": 2,
  "rides_with_threshold_crossing": 2,
  "threshold_windows_total": 59,
  "power_at_0_75": 187,
  "hr_at_0_75": 135,
  "z2_upper_power": 199,
  "z2_upper_source": "athlete_zones",
  "delta_pct": -6.0,
  "avg_time_above_0_75_pct": 67
}
```

| Field | Meaning |
| --- | --- |
| `rides_with_valid_data` | rides with a valid analysis |
| `rides_with_threshold_crossing` | subset in which alpha 1 actually reached the 0.65–0.85 band |
| `threshold_windows_total` | sum of `threshold_windows` over the crossing rides – the total evidence behind the estimate; null when no ride crossed |
| `power_at_0_75` / `hr_at_0_75` | mean over the crossing rides, **weighted by each ride's `threshold_windows`** so a ride that spent 40 windows near the threshold counts more than one that barely touched it; a ride without a window count carries weight 1 |
| `z2_upper_power` | the athlete's **configured** Zone 2 ceiling in watts |
| `z2_upper_source` | `athlete_zones` – from `metrics.power_zones_pct` (the Ride power zones set in intervals.icu); `ftp_75pct` – fallback to the Coggan default when no zones are configured |
| `delta_pct` | `(power_at_0_75 − z2_upper_power) / z2_upper_power × 100`; negative = LT1 estimate below the Zone 2 ceiling |
| `avg_time_above_0_75_pct` | mean share above 0.75 across valid rides |

### Supporting field – `metrics.power_zones_pct`

Upper bounds of the athlete's configured Ride power zones as % FTP, Z1
first, e.g. `[55, 75, 90, 105, 120, 150, 999]`. Read from the intervals.icu
`sportSettings`. The second entry is the Zone 2 ceiling used above.

---

## 5. How the coach reads it

The authoritative rules live in
[`coach-logic/interpretation-rules.md`](../coach-logic/interpretation-rules.md)
(section *DFA a1*) and the field reference in
[`coach-logic/input-schema.md`](../coach-logic/input-schema.md). In short:

**Quality first.** `valid: false` → do not interpret, mention the `reason`
once (strap contact / connection). `artifact_pct` 5–10 % → caution.
`power_at_0_75` null → the ride never touched the threshold; only
`time_above_0_75_pct` is informative.

**Per ride.**

| `time_above_0_75_pct` | reading |
| --- | --- |
| ≥ 80 % | genuine aerobic / Zone 2 session |
| 50–80 % | mixed; substantial time above LT1 despite "easy" power |
| < 50 % on a Base/Pyramidal ride | effectively a tempo ride; check pacing or fatigue |

**Per week.**

| `delta_pct` | reading |
| --- | --- |
| within ±10 % | no finding – within the method's individual uncertainty (limits of agreement around ±20 W) |
| −10 % to −15 % | upper Zone 2 was above LT1 on these days; favour the lower half of Z2 on long rides, or check freshness |
| below −15 % | zone ceiling clearly too high for this week's state (fatigue, heat, illness) or for this athlete's LT1/FTP ratio; do not raise intensity |
| above +10 % | aerobic threshold sits above the Zone 2 ceiling this week; Zone 2 may be ridden toward its ceiling |

**Division of labour with decoupling.** Durability (did the cardiovascular
response drift over the ride?) remains a `decoupling` reading. DFA a1 answers
a different question – where was the aerobic threshold today and how much of
the ride was below it? The two complement each other and never replace each
other. An earlier design that derived a second durability label from the
first-/second-half drift of alpha 1 was deliberately removed: it duplicated
decoupling on the same ride class with thinner evidence and would have forced
the coach to weigh two competing durability labels.

**The dataset covers one lookback, not a history.** LT1 moves far more from
day to day than FTP does, and the LT1/FTP ratio is individual (roughly
55–85 % FTP). Because earlier weeks are not in the dataset, the coach cannot
tell whether a deviation is new, persistent, or simply this athlete's
baseline. It states the observation, names plausible explanations, and leaves
the trend check and any zone or FTP change to the athlete in intervals.icu.

**Cross-check with FTP vs. eFTP.** `metrics.ftp_eftp_delta_pct` compares the
42-day power profile with the configured FTP – a six-week reference.
`aerobic_threshold_estimate.delta_pct` compares this week's DFA a1 threshold
with the configured Zone 2 ceiling – a lookback reading. Both use the same
configured FTP as yardstick, by independent methods, so together they answer:
*does this week's aerobic reading fit the longer-term performance picture?*

| `ftp_eftp_delta_pct` | `delta_pct` (DFA a1) | consistent reading (hypothesis) |
| --- | --- | --- |
| both negative, similar size | | week agrees with the six-week picture; configured FTP may be above the current state → suggest checking the FTP trend in intervals.icu |
| both positive, similar size | | form building at both ends; FTP may be below the current state → same, other direction |
| positive | ≈ 0 or negative | top end ahead of the aerobic threshold (after an interval block); raising FTP now would push Zone 2 above LT1 → caution with the FTP update |
| negative | ≈ 0 | aerobic threshold intact, top end dropped (late season) → no Zone 2 change |
| ≈ 0 | clearly negative | this week deviates on the aerobic side → read as day-form/readiness first (fatigue, heat, illness) |
| ≈ 0 | clearly positive | this week better than the six-week picture (fresh) → no change |
| both ≈ 0 | | consistent |
| one missing | | use the available signal alone |

"≈ 0" is within ±10 % on the DFA a1 side and within ±3 % on the eFTP side.

Example from a real dataset: eFTP −4.7 % and DFA a1 LT1 −6.0 % below the
Zone 2 ceiling – both negative, similar size. Recomputing the Zone 2 ceiling
from eFTP instead of FTP gives 190 W versus the DFA estimate of 187 W. The
consistent hypothesis is that the configured FTP was ~12 W above the current
state; whether that is a recent change or this athlete's normal ratio is for
the athlete to check against the history in intervals.icu. Note that −6 % is
also inside the ±10 % no-finding band on its own – it is the agreement with
eFTP that makes it worth mentioning at all.

---

## 6. Limits to keep in mind

- **Evidence level.** The 0.75 ≈ LT1 relationship is well supported on a
  group level; individual agreement varies by several percent. Treat it as an
  additional signal next to power, heart rate and decoupling, not as a
  substitute for a lactate or gas-exchange test.
- **Data quality dominates.** Garmin straps are less validated than Polar
  for beat-to-beat data; artifact rates are typically highest at the start
  of a ride and in the cold. The quality gate exists for this reason.
- **Latency.** A 120 s window reacts with a 1–2 minute delay to any change
  in power. Short surges disappear in the average; intervals are poorly
  suited. Long, steady rides are ideal.
- **Confounders.** Cadence and vibration, caffeine, heat, dehydration,
  illness and sleep debt all push alpha 1 down at a given power. That is
  partly the point (it reflects *internal* load), but it also means a single
  low value needs context.
- **Saturation.** Above ~1.2 and below ~0.4 the exponent is no longer
  discriminative. A ride spent entirely at 1.2 tells you it was easy, not how
  easy.
- **Thin crossings.** A `power_at_0_75` built on 3–5 windows of a ride that
  barely touched the threshold is a weak estimate; `threshold_windows` shows
  how much the value is worth. A ride near the upper end of Zone 2 gives a
  far more robust reading.
- **Individual LT1/FTP ratio.** The Coggan default puts the Zone 2 ceiling
  at 75 % FTP, but the true aerobic threshold ranges roughly from 55 % to
  85 % FTP between athletes. A negative `delta_pct` can therefore be an
  athlete's permanent normal rather than a finding – which is why the
  interpretation bands are wide (±10 %) and phrased as hypotheses.
- **No history in the dataset.** The coach sees one lookback. It cannot tell
  a new deviation from a persistent one; trend judgements belong to the
  athlete in intervals.icu, where the full history is available.

---

## 7. Configuration reference

All thresholds are constants at the top of
[`src/intervals_icu/dfa_a1.py`](../src/intervals_icu/dfa_a1.py) and
[`scripts/prepare_activities_for_coach.py`](../scripts/prepare_activities_for_coach.py):

| Constant | Default | Purpose |
| --- | --- | --- |
| `DEFAULT_WINDOW_SECONDS` | 120 | analysis window length |
| `DEFAULT_STEP_SECONDS` | 30 | window advance |
| `WARMUP_SECONDS` | 600 | ignored start of the ride |
| `SHORT_TERM_SCALES` | 4 … 16 | box sizes for alpha 1 |
| `ARTIFACT_JUMP_FRACTION` | 0.20 | beat-to-beat change treated as artifact |
| `MAX_WINDOW_ARTIFACT_PCT` | 5 | per-window rejection threshold |
| `MAX_ACTIVITY_ARTIFACT_PCT` | 10 | activity-wide `valid: false` threshold |
| `MIN_COVERAGE_PCT` | 50 | activity-wide `valid: false` threshold |
| `MIN_BEATS_PER_WINDOW` | 60 | minimum beats for a window |
| `MIN_VALID_WINDOWS` | 10 | minimum usable windows for a valid ride |
| `THRESHOLD_BAND` | 0.65–0.85 | windows counted toward `power_at_0_75` |
| `MIN_THRESHOLD_WINDOWS` | 3 | minimum windows in the band |
| `MIN_DFA_A1_DURATION_SECONDS` | 3600 | activity gate |
| `MAX_DFA_A1_Z5_PLUS_PCT` | 10 | activity gate |
| `MAX_DFA_A1_ANALYSES_PER_RUN` | 3 | newest qualifying rides analyzed per run |

---

## 8. References

All DOIs verified; links resolve to the open-access publisher pages.

- Peng C-K, Havlin S, Stanley HE, Goldberger AL (1995). *Quantification of
  scaling exponents and crossover phenomena in nonstationary heartbeat time
  series.* Chaos 5(1), 82–87.
  <https://doi.org/10.1063/1.166141>
- Hautala AJ, Mäkikallio TH, Seppänen T, Huikuri HV, Tulppo MP (2003).
  *Short-term correlation properties of R-R interval dynamics at different
  exercise intensity levels.* Clinical Physiology and Functional Imaging
  23(4), 215–223.
  <https://doi.org/10.1046/j.1475-097X.2003.00499.x>
- Gronwald T, Rogers B, Hoos O (2020). *Fractal Correlation Properties of
  Heart Rate Variability: A New Biomarker for Intensity Distribution in
  Endurance Exercise and Training Prescription?* Frontiers in Physiology
  11:550572.
  <https://doi.org/10.3389/fphys.2020.550572>
- Rogers B, Giles D, Draper N, Hoos O, Gronwald T (2021). *A New Detection
  Method Defining the Aerobic Threshold for Endurance Exercise and Training
  Prescription Based on Fractal Correlation Properties of Heart Rate
  Variability.* Frontiers in Physiology 11:596567.
  <https://doi.org/10.3389/fphys.2020.596567>
- Rogers B, Giles D, Draper N, Mourot L, Gronwald T (2021). *Detection of
  the Anaerobic Threshold in Endurance Sports: Validation of a New Method
  Using Correlation Properties of Heart Rate Variability.* Journal of
  Functional Morphology and Kinesiology 6(2), 38.
  <https://doi.org/10.3390/jfmk6020038>
