# Interpretation Rules

This document defines how the coach READS and CLASSIFIES training data.
It is the single source for all interpretation thresholds.

It does NOT prescribe actions — what to DO with an interpretation
(session selection, load changes, fueling strategy) is defined in
decision-process.md. Zone definitions live in training-zones.md.

---

## Form (Fatigue State)

form_absolute = CTL - ATL
form_pct      = (CTL - ATL) / CTL

| form_pct      | form_zone   | meaning |
| ------------- | ----------- | ------- |
| > +20%        | transition  | very fresh (often taper/detraining) |
| +5% to +20%   | fresh       | recovered, capacity to add load |
| -10% to +5%   | grey_zone   | normal training state |
| -30% to -10%  | optimal     | productive training zone |
| < -30%        | high_risk   | overreaching risk |

Always read form together with recovery indicators (HRV, resting HR,
subjective fatigue) and recent intensity — never in isolation.

## Training Readiness

`week_summary.training_readiness` estimates readiness for today's or the next
training session. It combines five independent domains: form, hard-session
recency, HRV, resting heart rate, and sleep. CTL, ATL, and TSB/form are one
combined form signal and must not be counted separately.

A session counts as hard when its TSS is at least 50% above current CTL,
regardless of its training distribution. In addition, `HIIT` and `Polarized`
sessions always count as hard. A `Threshold` session counts as hard with at
least 50 TSS or RPE 7+, preventing short, easy rides with incidental Z3/Z4 time
from resetting hard-session recency.

Score contributions:

| signal | condition | contribution |
| ------ | --------- | ------------ |
| form | fresh / grey_zone / optimal / transition / high_risk | +2 / +1 / 0 / +1 / -3 |
| hard-session recency | 0 / 1 / 2 / 3+ days | -3 / -1 / +1 / +2 |
| HRV vs 7-day average | ≤ -10% / ≤ -5% / ≥ +5% / ≥ +10% | -2 / -1 / +1 / +2 |
| resting HR vs 7-day average | ≥ +7% / ≥ +3% / ≤ -3% / ≤ -7% | -2 / -1 / +1 / +2 |
| sleep | POOR or < 6h / AVG or < 7h / GOOD or GREAT and ≥ 7h | -2 / -1 / +1 |

The HRV and resting-HR `trend_7d` adjusts the contribution by one point in
the matching direction, bounded to -2 through +2.

Base colors are green for scores ≥ +2, yellow for -2 through +1, and red for
scores ≤ -3. Safety rules override the score:

- `high_risk` form or a hard session today forces red.
- Two or more adverse signals among HRV, resting HR, and sleep force red.
- A hard session one day ago caps readiness at yellow.
- With no usable signal, status is `unknown` rather than green.

Confidence reflects available domains: high for 4–5, medium for 2–3, and low
for 0–1. Missing wellness data is not adverse; it only lowers confidence.
Weight trend remains context and does not affect acute readiness because
short-term weight changes can reflect hydration and fueling.

---

## Decoupling (Aerobic Durability)

Power:HR drift over an effort. Valid **ONLY for endurance-oriented steady efforts**:
- Base / Pyramidal / Threshold rides
- Duration ≥ 90 minutes
- NOT VO2max / short high-intensity sessions
- NOT interval work or variable efforts

For rides outside these conditions, durability signal is limited or not applicable.

| decoupling | label |
| ---------- | ----- |
| < 5%       | excellent durability |
| 5–8%       | moderate drift |
| 8–10%      | high drift |
| > 10%      | significant limitation |

Always interpret decoupling together with fueling (below): high
decoupling alone does not prove a durability limitation.

---

## DFA a1 (In-Ride Aerobic Threshold Marker)

DFA alpha 1 is a scaling exponent of the R-R intervals recorded during the
ride. It **falls with rising intensity**; ≈ 0.75 marks the aerobic threshold
(LT1/VT1), ≈ 0.50 is discussed as the anaerobic threshold. It is an
**additional, complementary signal** — never use it to set or override
training zones on its own, and never confuse it with the nightly
`metrics.hrv` (recovery signal).

Available in `activities[].dfa_a1_summary` (per ride) and
`week_summary.aerobic_threshold_estimate` (lookback aggregate). Both are
omitted when no ride carries usable R-R data; silence is not a limitation.

**DFA a1 is never a warning.** Only rides that were ridden as aerobic
sessions (`Base` / `Pyramidal`, no threshold, vo2max or race tag) are
analyzed. Threshold workouts, HIIT, races and fast group rides carry no
`dfa_a1_summary` by design — do not comment on their absence, and never
infer anything about such rides from the week aggregate. A low
`time_above_0_75_pct` is a *zone-placement observation* about a ride the
athlete meant to be easy, phrased as information, not as a fault.

### Quality gate (read first)
| condition | reading |
| --------- | ------- |
| `valid = false` | do not interpret; mention `reason` (strap contact, artifacts) at most once |
| `artifact_pct` 5–10 % | interpret with caution |
| `threshold_windows` < 3 (→ `power_at_0_75` null) | the ride did not touch the threshold; only `time_above_0_75_pct` is informative |

### Per ride
| signal | reading |
| ------ | ------- |
| `time_above_0_75_pct` ≥ 80 % | genuine aerobic/Zone-2 session |
| `time_above_0_75_pct` 50–80 % | mixed; substantial time above LT1 despite "easy" power |
| `time_above_0_75_pct` < 50 % | the easy ride was effectively tempo; mention once as context for pacing or freshness, not as an error |
| `power_at_0_75_pct_ftp` vs. Zone 2 ceiling (`metrics.power_zones_pct[1]`, default 75 %) | same reading as the week-level `delta_pct` table below, but for one day; day-to-day swings of several points at a stable HR (`hr_at_0_75`) point to freshness, heat or sleep rather than fitness |

### Week level (`aerobic_threshold_estimate`)
| `delta_pct` | reading |
| ----------- | ------- |
| within ±10 % | no finding; the deviation is within the method's uncertainty (individual limits of agreement around ±20 W) |
| −10 % to −15 % | upper Zone 2 was above LT1 on these days; favour the lower half of Z2 for long rides, or check freshness |
| below −15 % | zone ceiling clearly too high for this week's state (fatigue, heat, illness) or for this athlete's LT1/FTP ratio; do not raise intensity |
| above +10 % | aerobic threshold sits above the Zone 2 ceiling this week; Zone 2 may be ridden toward its ceiling |

`delta_pct` is a reading of **this lookback only**. The dataset does not
contain earlier weeks, so the coach cannot judge whether a deviation is new,
persistent or the athlete's normal — the LT1/FTP ratio is individual (roughly
55–85 % FTP) and a steady negative `delta_pct` can simply be this athlete's
baseline. State the observation, name possible explanations, and leave the
trend check and any zone or FTP change to the athlete in intervals.icu.
`threshold_windows_total` is the evidence behind the week estimate: a small
total (< 10) means the rides barely touched the threshold, so treat
`power_at_0_75` and `delta_pct` as weak.

### Cross-check with FTP vs. eFTP
`metrics.ftp_eftp_delta_pct` compares the 42-day power profile with the
configured FTP (a six-week reference). `aerobic_threshold_estimate.delta_pct`
compares this week's DFA a1 threshold with the configured Zone 2 ceiling (a
lookback reading). Both are measured against the same configured FTP by
independent methods, so reading them together answers one question: **does
this week's aerobic reading fit the longer-term performance picture?**

| `ftp_eftp_delta_pct` | `delta_pct` (DFA a1) | consistent reading (hypothesis, not diagnosis) |
| -------------------- | -------------------- | ---------------------------------------------- |
| both negative, similar size | | this week's reading agrees with the six-week picture; one plausible explanation is that the configured FTP is above the current state — mention it, suggest the athlete checks the FTP trend in intervals.icu |
| both positive, similar size | | form is building at both ends; the configured FTP may be below the current state — same suggestion, in the other direction |
| positive | ≈ 0 or negative | top-end performance is ahead of the aerobic threshold this week (typical after an interval block); if the athlete raises FTP now, Zone 2 moves above LT1 — advise caution with the FTP update rather than higher Z2 |
| negative | ≈ 0 | aerobic threshold intact this week while top end has dropped (typical late season); no Zone 2 change indicated |
| ≈ 0 | clearly negative | this week deviates from the six-week picture on the aerobic side; treat as a day-form/readiness signal (fatigue, heat, illness) before considering a base deficit |
| ≈ 0 | clearly positive | this week's aerobic reading is better than the six-week picture suggests (fresh, well recovered); no change indicated |
| both ≈ 0 | | consistent; nothing to report |
| one of the two missing | | use the available signal alone; do not claim a cross-check |

"≈ 0" means within ±10 % for the DFA a1 side and within ±3 % for the eFTP
side. The cross-check adds or removes confidence in an observation; it does
not establish a trend and never replaces the athlete's decision in
intervals.icu.

### Relationship to decoupling
- Decoupling answers "did the cardiovascular response drift over the
  ride?" (durability); DFA a1 answers "where was the aerobic threshold today
  and how much of the ride was below it?" (intensity placement).
- They do not replace each other: durability stays a decoupling reading,
  threshold placement stays a DFA a1 reading.
- Low DFA a1 share above 0.75 with low decoupling → steady but too hard.
- High decoupling with high DFA a1 share above 0.75 → the ride was aerobic
  but durability still faded; look at fueling, heat and sleep first.

---

## Anaerobic Capacity (W')

w_prime_drop_pct = w_prime_bal_drop_j / w_prime_j × 100

Diagnostic signals:
- Long ride with w_prime_drop_pct > 20% → pacing too aggressive; durability at risk
- Aerobic/endurance ride with w_prime_usage_pct > 15% → unintended intensity / spiky riding
- Repeated large W' depletions across the week → anaerobic fatigue may be limiting

(Corresponding actions are defined in decision-process.md.)

---

## Fueling

### Requirement by duration
| duration  | fueling |
| --------- | ------- |
| < 1.5h    | not required |
| 1.5–2.0h  | optional |
| > 2.0h    | required |

### Carbohydrate targets
- moderate / endurance rides: 60–80 g/h
- long rides / high load:     80–90 g/h

### Fueling ratio (carbs_ingested / carbs_used)
| ratio    | classification |
| -------- | -------------- |
| < 0.4    | significant deficit |
| 0.4–0.7  | moderate deficit |
| > 0.7    | good |

### Fueling × durability (combined reading)
| decoupling | carbs | interpretation |
| ---------- | ----- | -------------- |
| high       | low   | likely fueling limitation |
| high       | good  | aerobic durability limitation |
| low        | good  | good durability and fueling |
| low        | low   | efficient, but performance may still be limited |

---

## Primary Limiter Detection

Identify the single primary limiter from combined signals:

- VO2max → low p5min / VO2max; little recent high-intensity work
- Threshold (FTP) → declining power in sustained efforts; cannot hold FTP
- Aerobic durability → high decoupling (>8–10%) on steady efforts; power drop in long rides; DFA a1 `delta_pct` below −15 % on fresh days as supporting evidence
- Fueling / energy availability → low carbs/h, low fueling ratio, high decoupling with low intake
- Anaerobic / repeatability → repeated W' depletion limiting late efforts (discipline-dependent)

If several signals point to fueling, resolve fueling FIRST — an
underfueled session can mimic a fitness limitation.

(Limiter-based session prescription is defined in decision-process.md.)

---

## Activity Classification by Tag

Tags are the highest-priority classifier and override interval detection
and automatic distribution.

Priority: tags > interval detection > automatic classification

If a session has multiple canonical tags, all matching tag mappings apply.
Tags do not compete. A single session can classify into multiple ride types
and should be counted in each mapped domain.

### Tag taxonomy (canonical source)
Format: "<domain>-<level>"
- domains: vo2max, lactate-threshold, aerobic-threshold, recovery, race-specific
- levels:  low, moderate, high

These prefixes are shared with the workout library (decision-process.md)
and with library filter tooling. Do not rename without updating all three.

### Tag → ride_type mapping
- vo2max-*            → vo2
- lactate-threshold-* → threshold
- aerobic-threshold-*:
    - duration ≥ 2h   → long_ride
    - else            → endurance
- recovery-*          → recovery
- race-specific-*     → race

### Multiple tags on one session (CRITICAL)
- Resolve each tag independently using the mapping above.
- Keep all resolved ride types; do not collapse to a single class.
- Example: tags `aerobic-threshold-high` and `vo2max-moderate` classify
    as both `long_ride` and `vo2` (for duration ≥ 2h), and the session counts
    toward both domains.

---

## Cross-Cutting Principle

Never interpret high decoupling, declining power, or high fatigue as a
purely physiological limitation without first checking fueling and recent
load. Always combine: form + recovery + fueling + recent intensity.
